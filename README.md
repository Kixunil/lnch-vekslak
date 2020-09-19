LN channel vekslak
==================

Allows you to open possibly pre-funded channels on the street.

BIG FAT WARNING #0
------------------

**You MUST review the code! By running the code WITHOUT reviewing it YOU AGREE to pay PENALTY of 150000 satoshis to the author of this code. Do NOT use if you don't want to pay nor review the code!**

About
-----

This is a (too) simple, little server allowing you to open a channel with anyone using Bitcoin Lightning Wallet on the street. Just open the admin interface, enter the amounts and let the other party scan the QR code.

This way, you can easily sell pre-opened channels. Once [zero-conf spending push amount is allowed](https://github.com/lightningnetwork/lightning-rfc/issues/565), this will allow your customers to pay with opened channels immediately.

BIG FAT WARNIG #1
-----------------

**This code purposefully doesn't implement encryption, nor authentication! Use only with properly configured nginx! Do NOT use on multi-user system!!!**

How to use
----------

* Review the code or decide to pay me a penalty
* Install nginx
* Configure nginx to use basic HTTP authentication and forward to port 8050
* Run `./server.py your-domain.tld`, https is added by default. You may configure a rewrite in nginx to use some suffix like `/vekslak` - in that case, append the same suffix to `your-domain.tld`.
* Go out, sell channels.
* Refill your bitcoins
* Repeat selling
