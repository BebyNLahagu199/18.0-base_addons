-  Models To use the QR Code, the models need to inherit
   ``qr.code.mixin`` model.

-  Data For data in the QR Code, write down the data code inside the
   ``prepare_qr_value()`` function.

-  The QR Code data is encrypted using ``Fernet`` if the Key is set in
   the settings.

-  The QR Code is created using ``qrcode`` library from Python.
