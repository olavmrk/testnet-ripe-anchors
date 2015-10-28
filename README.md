testnet-ripe-anchors
===================

`testnet-ripe-anchors.py` is a Python-script that checks network connectivity by contacting a random subset of [RIPE Atlas Anchors](https://atlas.ripe.net/about/anchors/).
It is inspired by a [blog post at RIPE labs](https://labs.ripe.net/Members/stephane_bortzmeyer/checking-your-internet-connectivity-with-ripe-atlas-anchors).

To test connectivity, it tries to send a HTTP request to a set of RIPE Atlas Anchors.


Quick start
-----------

*Note*:
If you get an error about being unable to import the requests-library, you will need to install it.
See the section about dependencies belof.


To test connectivity to 5% of the RIPE Atlas Anchors, run:

```
$ ./testnet-ripe-anchors.py
14 / 14 OK
```

If you only have IPv4 connectivity, you may want to run:

```
$ ./testnet-ripe-anchors.py --ipv4
7 / 7 OK
```


Options
-------

There are a number of options to control the behavior of this program.
To see a full list of options, run `./testnet-ripe-anchors.py --help`


##### `--all`

Try to connect to all available targets.

Example:

```
$ ./testnet-ripe-anchors.py --all
294 / 298 OK
```


##### `--count`

Number of targets to test against.

This can either be an absolute number, or a percentage of available targets.
For example, to test against 30 targets:

```
$ ./testnet-ripe-anchors.py --count=30
30 / 30 OK
```

To test against 10% of available targets:

```
$ ./testnet-ripe-anchors.py --count=10%
29 / 29 OK
```


##### `--fail-threshold`

Failure threshold.
Exit with an error status if less than this number of targets respond.
This can be specified as both a percentage and as an absolute value.

Example using an absolute value:

```
$ ./testnet-ripe-anchors.py --count=50 --fail-threshold=40
35 / 50 OK
$ echo $?
1
```

Or using a percentage:

```
$ ./testnet-ripe-anchors.py --count=50 --fail-threshold=75%
35 / 50 OK
$ echo $?
1
```


##### `--ipv4`

Test only IPv4 targets.

Example:

```
$ ./testnet-ripe-anchors.py --all --ipv4
148 / 149 OK
```


##### `--ipv6`

Test only IPv6 targets.

Example:

```
$ ./testnet-ripe-anchors.py --all --ipv6
147 / 149 OK
```


##### `--output`

Output format for presenting the output.

The following output formats are available:

###### `count`

A simple count of the number of targets reached.
This is most useful when used together with the `--count` option:

```
$ ./testnet-ripe-anchors.py --count=50 --output=count
48
```

###### `count_total`

Print the number of targets reached and the number of targets tried, as two numbers on one line:

```
$ ./testnet-ripe-anchors.py --output=count_total
13 14
```

Or in a shell script:

```
#!/bin/bash
set -e # Exit on error
./testnet-ripe-anchors.py --output=count_total | (
  read OK TOTAL
  echo "OK: $OK"
  echo "Total: $TOTAL"
)
```

###### `percent`

The percentage of test targets that we were able to reach:

```
$ ./testnet-ripe-anchors.py --output=percent
100.00
```

###### `verbose`

This is a human readable presentation of the result:

```
$ ./testnet-ripe-anchors.py --output=verbose
14 / 14 OK
```


Dependencies
------------

To run this project, you need the [requests](http://python-requests.org/) library installed.
On a relatively recent Linux distribution, you can use the requests-library included with your distro.
For example, on Debian Jessie:

```
$ apt-get install python-requests
```

*Note*:
The version of the requests library included in Debian Wheezy is too old to support tests using IPv6.

If you cannot use the version of requests that is included in your Linux distribution, you can install it in a [Virtual Environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/):

```
$ virtualenv testnet-ve
New python executable in testnet-ve/bin/python
Installing distribute.............................................................................................................................................................................................done.
Installing pip...............done.
$ ./testnet-ve/bin/pip install requests
Downloading/unpacking requests
  Downloading requests-2.8.1.tar.gz (480Kb): 480Kb downloaded
  Running setup.py egg_info for package requests

Installing collected packages: requests
  Running setup.py install for requests

Successfully installed requests
Cleaning up...
$ ./testnet-ve/bin/python testnet-ripe-anchors.py
14 / 14 OK
```
