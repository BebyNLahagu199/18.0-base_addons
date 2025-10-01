/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {Model} from "@web/model/model";
import {session} from "@web/session";
import {browser} from "@web/core/browser/browser";
import {formatDateTime, parseDate, parseDateTime} from "@web/core/l10n/dates";
import {KeepLast} from "@web/core/utils/concurrency";

const DATE_GROUP_FORMATS = {
    year: "yyyy",
    quarter: "'Q'q yyyy",
    month: "MMMM yyyy",
    week: "'W'WW yyyy",
    day: "dd MMM yyyy",
};

export class MapsModel extends Model {
    setup(params, {notification, http}) {
        this.notification = notification;
        this.http = http;

        this.metaData = {
            ...params,
            mapBoxToken: session.map_box_token || "",
        };
        this.data = {
            count: 0,
            fetchingCoordinates: false,
            groupByKey: false,
            isGrouped: false,
            numberOfLocatedRecords: 0,
            locationIds: [],
            locations: [],
            locationToCache: [],
            recordGroups: [],
            records: [],
            routes: [],
            routingError: null,
            shouldUpdatePosition: true,
            useMapBoxAPI: Boolean(this.metaData.mapBoxToken),
        };

        this.coordinateFetchingTimeoutHandle = undefined;
        this.shouldFetchCoordinates = false;
        this.keepLast = new KeepLast();
    }
    /**
     * @param {any} params
     * @returns {Promise<void>}
     */
    async load(params) {
        if (this.coordinateFetchingTimeoutHandle !== undefined) {
            this.stopFetchingCoordinates();
        }
        const metaData = {
            ...this.metaData,
            ...params,
        };
        this.data = await this._fetchData(metaData);
        this.metaData = metaData;

        this.notify();
    }
    /**
     * Tells the model to stop fetching coordinates.
     * In OSM mode, the model starts to fetch coordinates once every second after the
     * model has loaded.
     * This fetching has to be done every second if we don't want to be banned from OSM.
     * There are typically two cases when we need to stop fetching:
     * - when component is about to be unmounted because the request is bound to
     *   the component and it will crash if we do so.
     * - when calling the `load` method as it will start fetching new coordinates.
     */
    stopFetchingCoordinates() {
        browser.clearTimeout(this.coordinateFetchingTimeoutHandle);
        this.coordinateFetchingTimeoutHandle = undefined;
        this.shouldFetchCoordinates = false;
    }

    // ----------------------------------------------------------------------
    // Protected
    // ----------------------------------------------------------------------

    /**
     * Adds the corresponding location to a record.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     */
    _addLocationToRecord(metaData, data) {
        for (const record of data.records) {
            for (const location of data.locations) {
                let recordLocationId = null;
                if (metaData.locationField === "id") {
                    recordLocationId = record.id;
                } else {
                    recordLocationId = record[metaData.locationField].id;
                }

                if (recordLocationId === location.id) {
                    record.location = location;
                    data.numberOfLocatedRecords++;
                }
            }
        }
    }

    /**
     * The location's coordinates should be between -90 <= latitude <= 90 and -180 <= longitude <= 180.
     *
     * @protected
     * @param {Object} location
     * @param {Number} location.location_latitude latitude of the location
     * @param {Number} location.location_longitude longitude of the location
     * @returns {Boolean}
     */
    _checkCoordinatesValidity(location) {
        if (
            location.location_latitude &&
            location.location_longitude &&
            location.location_latitude >= -90 &&
            location.location_latitude <= 90 &&
            location.location_longitude >= -180 &&
            location.location_longitude <= 180
        ) {
            return true;
        }
        return false;
    }

    /**
     * Handles the case of an empty map.
     * Handles the case where the model is res_location.
     * Fetches the records according to the model given in the arch.
     * If the records has no location_id field it is sliced from the array.
     *
     * @protected
     * @param {Object} metaData
     * @returns {Promise<any>}
     */
    async _fetchData(metaData) {
        const data = {
            count: 0,
            fetchingCoordinates: false,
            groupByKey: metaData.groupBy.length ? metaData.groupBy[0] : false,
            isGrouped: metaData.groupBy.length > 0,
            numberOfLocatedRecords: 0,
            locationIds: [],
            locations: [],
            locationToCache: [],
            recordGroups: [],
            records: [],
            routes: [],
            routingError: null,
            shouldUpdatePosition: true,
            useMapBoxAPI: Boolean(metaData.mapBoxToken),
        };

        // Case of empty map
        // STEF: this is used to handle incorrect maps definition
        if (!metaData.locationField) {
            data.recordGroups = [];
            data.records = [];
            data.routes = [];
            return this.keepLast.add(Promise.resolve(data));
        }
        const results = await this.keepLast.add(this._fetchRecordData(metaData, data));

        const datetimeFields = metaData.fieldNames.filter(
            (name) => metaData.fields[name].type === "datetime"
        );
        for (const record of results.records) {
            // Convert date fields from UTC to local timezone
            for (const field of datetimeFields) {
                if (record[field]) {
                    const dateUTC = luxon.DateTime.fromFormat(
                        record[field],
                        "yyyy-MM-dd HH:mm:ss",
                        {zone: "UTC"}
                    );
                    record[field] = formatDateTime(dateUTC, {
                        format: "yyyy-MM-dd HH:mm:ss",
                    });
                }
            }
        }

        data.records = results.records;
        data.count = results.length;
        if (data.isGrouped) {
            data.recordGroups = await this._getRecordGroups(metaData, data);
        } else {
            data.recordGroups = [];
        }

        data.locationIds = [];
        for (const record of data.records) {
            if (metaData.locationField === "id") {
                data.locationIds.push(record.id);
                record.location_id = [record.id];
            } else if (record[metaData.locationField]) {
                data.locationIds.push(record[metaData.locationField].id);
            }
        }

        data.locationIds = [...new Set(data.locationIds)];
        await this._locationFetching(metaData, data);

        return data;
    }

    /**
     * Fetch the records for a given model.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @returns {Promise}
     */
    _fetchRecordData(metaData, data) {
        const fieldNames = data.groupByKey
            ? metaData.fieldNames.concat(data.groupByKey.split(":")[0])
            : metaData.fieldNames;
        const specification = {};
        for (const fieldName of fieldNames) {
            specification[fieldName] = {};
            if (
                ["many2one", "one2many", "many2many"].includes(
                    metaData.fields[fieldName].type
                )
            ) {
                specification[fieldName].fields = {display_name: {}};
            }
        }
        const orderBy = [];
        if (metaData.defaultOrder) {
            orderBy.push(metaData.defaultOrder.name);
            if (metaData.defaultOrder.asc) {
                orderBy.push("ASC");
            }
        }
        return this.orm.webSearchRead(metaData.resModel, metaData.domain, {
            specification,
            limit: metaData.limit,
            offset: metaData.offset,
            order: orderBy.join(" "),
            context: metaData.context,
        });
    }

    /**
     * This function convert the addresses to coordinates using the openStreetMap api.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @param {Object} record this object contains the record fetched from the database.
     * @returns {Promise} result is an array that contains the result in descendant order of relevance
     *      result[i].lat is the latitude of the converted address
     *      result[i].lon is the longitude of the converted address
     *      result[i].importance is a number that the relevance of the result the closer the number is to one the best it is.
     */
    _fetchCoordinatesFromAddressOSM(metaData, data, record) {
        const address = encodeURIComponent(
            record.contact_address_complete.replace("/", " ")
        );
        const encodedUrl = `https://nominatim.openstreetmap.org/search?q=${address}&format=jsonv2`;
        return this.http.get(encodedUrl);
    }

    /**
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @param {Number[]} ids contains the ids from the locations
     * @returns {Promise}
     */
    _fetchRecordsLocation(metaData, data, ids) {
        let model = metaData.resModel;
        const domain = [
            ["contact_address_complete", "!=", "False"],
            ["id", "in", ids],
        ];
        const fields = [
            "contact_address_complete",
            "location_latitude",
            "location_longitude",
        ];
        if (metaData.locationField !== "id") {
            model = metaData.fields[metaData.locationField].relation;
        }
        return this.orm.searchRead(model, domain, fields);
    }

    /**
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @returns {Object} the fetched records grouped by the groupBy field.
     */
    async _getRecordGroups(metaData, data) {
        const [fieldName, subGroup] = data.groupByKey.split(":");
        const fieldType = metaData.fields[fieldName].type;
        const groups = {};
        function addToGroup(id, name, record) {
            if (!groups[id]) {
                groups[id] = {
                    name,
                    records: [],
                };
            }
            groups[id].records.push(record);
        }
        for (const record of data.records) {
            const value = record[fieldName];
            let id = null,
                name = null;
            if (["one2many", "many2many"].includes(fieldType)) {
                if (value.length) {
                    for (const r of value) {
                        addToGroup(r.id, r.display_name, record);
                    }
                } else {
                    id = name = this._getEmptyGroupLabel();
                    addToGroup(id, name, record);
                }
            } else {
                if (["date", "datetime"].includes(fieldType) && value) {
                    const date =
                        fieldType === "date" ? parseDate(value) : parseDateTime(value);
                    id = name = date.toFormat(DATE_GROUP_FORMATS[subGroup]);
                } else if (fieldType === "boolean") {
                    id = name = value ? _t("Yes") : _t("No");
                } else if (fieldType === "many2one" && value) {
                    id = value.id;
                    name = value.display_name;
                } else {
                    id = value;
                    name = value;
                }
                if (!id && !name) {
                    id = name = this._getEmptyGroupLabel();
                }
                addToGroup(id, name, record);
            }
        }
        return groups;
    }

    /**
     * Notifies the fetched coordinates to server and controller.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     */
    _notifyFetchedCoordinate(metaData, data) {
        this._writeCoordinatesUsers(metaData, data);
        data.shouldUpdatePosition = false;
        this.notify();
    }

    /**
     * Calls (without awaiting) _openStreetMapAPIAsync with a delay of 1000ms
     * to not get banned from openstreetmap's server.
     *
     * Tests should patch this function to wait for coords to be fetched.
     *
     * @see _openStreetMapAPIAsync
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @returns {Promise}
     */
    _openStreetMapAPI(metaData, data) {
        this._openStreetMapAPIAsync(metaData, data);
        return Promise.resolve();
    }
    /**
     * Handles the case where the selected api is open street map.
     * Iterates on all the locations and fetches their coordinates when they're not set.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @returns {Promise}
     */
    _openStreetMapAPIAsync(metaData, data) {
        // Group locations by address to reduce address list
        const addressLocationMap = new Map();
        for (const location of data.locations) {
            if (
                location.contact_address_complete &&
                (!location.location_latitude || !location.location_longitude)
            ) {
                if (!addressLocationMap.has(location.contact_address_complete)) {
                    addressLocationMap.set(location.contact_address_complete, []);
                }
                addressLocationMap
                    .get(location.contact_address_complete)
                    .push(location);
                location.fetchingCoordinate = true;
            } else if (!this._checkCoordinatesValidity(location)) {
                location.location_latitude = undefined;
                location.location_longitude = undefined;
            }
        }

        // `fetchingCoordinates` is used to display the "fetching banner"
        // We need to check if there are coordinates to fetch before reload the
        // view to prevent flickering
        data.fetchingCoordinates = addressLocationMap.size > 0;
        this.shouldFetchCoordinates = true;
        const fetch = async () => {
            const locationsList = Array.from(addressLocationMap.values());
            for (let i = 0; i < locationsList.length; i++) {
                await new Promise((resolve) => {
                    this.coordinateFetchingTimeoutHandle = browser.setTimeout(
                        resolve,
                        this.constructor.COORDINATE_FETCH_DELAY
                    );
                });
                if (!this.shouldFetchCoordinates) {
                    return;
                }
                const locations = locationsList[i];
                try {
                    const coordinates = await this._fetchCoordinatesFromAddressOSM(
                        metaData,
                        data,
                        locations[0]
                    );
                    if (!this.shouldFetchCoordinates) {
                        return;
                    }
                    if (coordinates.length) {
                        for (const location of locations) {
                            location.location_longitude = parseFloat(
                                coordinates[0].lon
                            );
                            location.location_latitude = parseFloat(coordinates[0].lat);
                            data.locationToCache.push(location);
                        }
                    }
                    for (const location of locations) {
                        location.fetchingCoordinate = false;
                    }
                    data.fetchingCoordinates = i < locationsList.length - 1;
                    this._notifyFetchedCoordinate(metaData, data);
                } catch {
                    for (const location of data.locations) {
                        location.fetchingCoordinate = false;
                    }
                    data.fetchingCoordinates = false;
                    this.shouldFetchCoordinates = false;
                    this.notification.add(
                        _t("OpenStreetMap's request limit exceeded, try again later."),
                        {type: "danger"}
                    );
                    this.notify();
                }
            }
        };
        return fetch();
    }

    /**
     * Fetches the location which ids are contained in the the array locationIds
     * if the token is set it uses the mapBoxApi to fetch address and route
     * if not is uses the openstreetmap api to fetch the address.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @param {Number[]} locationIds this array contains the ids from the location that are linked to records
     * @returns {Promise}
     */
    async _locationFetching(metaData, data) {
        data.locations = data.locationIds.length
            ? await this.keepLast.add(
                  this._fetchRecordsLocation(metaData, data, data.locationIds)
              )
            : [];
        this._addLocationToRecord(metaData, data);
        if (data.useMapBoxAPI) {
            return this.keepLast
                .add(this._maxBoxAPI(metaData, data))
                .then(() => {
                    this._writeCoordinatesUsers(metaData, data);
                })
                .catch((err) => {
                    this._mapBoxErrorHandling(metaData, data, err);
                    data.useMapBoxAPI = false;
                    return this._openStreetMapAPI(metaData, data);
                });
        }
        return this._openStreetMapAPI(metaData, data).then(() => {
            this._writeCoordinatesUsers(metaData, data);
        });
    }

    /**
     * Writes location_longitude and location_latitude of the res.location model.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @returns {Promise}
     */
    async _writeCoordinatesUsers(metaData, data) {
        const locations = data.locationToCache;
        data.locationToCache = [];
        if (locations.length) {
            await this.orm.call(
                metaData.resModel,
                "update_latitude_longitude",
                [locations],
                {
                    context: metaData.context,
                }
            );
        }
    }

    // MapBox Sections

    /**
     * This function convert the addresses to coordinates using the mapbox API.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @param {Object} record this object contains the record fetched from the database.
     * @returns {Promise} result.query contains the query the the api received
     *      result.features contains results in descendant order of relevance
     */
    _fetchCoordinatesFromAddressMB(metaData, data, record) {
        const address = encodeURIComponent(record.contact_address_complete);
        const token = metaData.mapBoxToken;
        const encodedUrl = `https://api.mapbox.com/geocoding/v5/mapbox.places/${address}.json?access_token=${token}&cachebuster=1552314159970&autocomplete=true`;
        return this.http.get(encodedUrl);
    }

    /**
     * Fetch the route from the mapbox api.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @returns {Promise}
     *      results.geometry.legs[i] contains one leg (i.e: the trip between two markers).
     *      results.geometry.legs[i].steps contains the sets of coordinates to follow to reach a point from an other.
     *      results.geometry.legs[i].distance: the distance in meters to reach the destination
     *      results.geometry.legs[i].duration the duration of the leg
     *      results.geometry.coordinates contains the sets of coordinates to go from the first to the last marker without the notion of waypoint
     */
    _fetchRoute(metaData, data) {
        const coordinatesParam = data.records
            .filter(
                (record) =>
                    record.location.location_latitude &&
                    record.location.location_longitude
            )
            .map(
                ({location}) =>
                    `${location.location_longitude},${location.location_latitude}`
            );
        const address = encodeURIComponent(coordinatesParam.join(";"));
        const token = metaData.mapBoxToken;
        const encodedUrl = `https://api.mapbox.com/directions/v5/mapbox/driving/${address}?access_token=${token}&steps=true&geometries=geojson`;
        return this.http.get(encodedUrl);
    }

    /**
     * Converts a MapBox error message into a custom translatable one.
     *
     * @protected
     * @param {String} message
     * @returns {String}
     */
    _getErrorMessage(message) {
        const ERROR_MESSAGES = {
            "Too many coordinates; maximum number of coordinates is 25": _t(
                "Too many routing points (maximum 25)"
            ),
            "Route exceeds maximum distance limitation": _t(
                "Some routing points are too far apart"
            ),
            "Too Many Requests": _t("Too many requests, try again in a few minutes"),
        };
        return ERROR_MESSAGES[message];
    }

    _getEmptyGroupLabel() {
        return _t("None");
    }

    /**
     * Handles the case where the selected api is MapBox.
     * Iterates on all the locations and fetches their coordinates when they're not set.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @returns {Promise} if there's more than 2 located records and the routing option is activated it returns a promise that fetches the route
     *      resultResult is an object that contains the computed route
     *      or if either of these conditions are not respected it returns an empty promise
     */
    _maxBoxAPI(metaData, data) {
        const promises = [];
        for (const location of data.locations) {
            if (
                location.contact_address_complete &&
                (!location.location_latitude || !location.location_longitude)
            ) {
                promises.push(
                    this._fetchCoordinatesFromAddressMB(metaData, data, location).then(
                        (coordinates) => {
                            if (coordinates.features.length) {
                                location.location_longitude = parseFloat(
                                    coordinates.features[0].geometry.coordinates[0]
                                );
                                location.location_latitude = parseFloat(
                                    coordinates.features[0].geometry.coordinates[1]
                                );
                                data.locationToCache.push(location);
                            }
                        }
                    )
                );
            } else if (!this._checkCoordinatesValidity(location)) {
                location.location_latitude = undefined;
                location.location_longitude = undefined;
            }
        }
        return Promise.all(promises).then(() => {
            data.routes = [];
            if (
                data.numberOfLocatedRecords > 1 &&
                metaData.routing &&
                !data.groupByKey
            ) {
                return this._fetchRoute(metaData, data).then((routeResult) => {
                    if (routeResult.routes) {
                        data.routes = routeResult.routes;
                    } else {
                        data.routingError = this._getErrorMessage(routeResult.message);
                    }
                });
            }
            return Promise.resolve();
        });
    }

    /**
     * Handles the displaying of error message according to the error.
     *
     * @protected
     * @param {Object} metaData
     * @param {Object} data
     * @param {Object} err contains the error returned by the requests
     * @param {Number} err.status contains the status_code of the failed http request
     */
    _mapBoxErrorHandling(metaData, data, err) {
        switch (err.status) {
            case 401:
                this.notification.add(
                    _t(
                        "The view has switched to another provider but functionalities will be limited"
                    ),
                    {
                        title: _t("Token invalid"),
                        type: "danger",
                    }
                );
                break;
            case 403:
                this.notification.add(
                    _t(
                        "The view has switched to another provider but functionalities will be limited"
                    ),
                    {
                        title: _t("Unauthorized connection"),
                        type: "danger",
                    }
                );
                break;
            case 422:
                // Max. addresses reached
                break;
            case 429:
                // Max. requests reached
                data.routingError = this._getErrorMessage(err.responseJSON.message);
                break;
            case 500:
                this.notification.add(
                    _t(
                        "The view has switched to another provider but functionalities will be limited"
                    ),
                    {
                        title: _t("MapBox servers unreachable"),
                        type: "danger",
                    }
                );
        }
    }
}

MapsModel.services = ["notification", "http"];
MapsModel.COORDINATE_FETCH_DELAY = 1000;
