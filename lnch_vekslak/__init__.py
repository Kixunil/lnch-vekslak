import secrets
import bech32
from bottle import route, request, run, static_file
import subprocess
import sys
import json
from pathlib import Path
import requests
import toml

def fail(message):
	print(message, file=sys.stderr)
	sys.exit(1)

def encode_lnurl(url):
	hrp = "lnurl"
	return bech32.bech32_encode(hrp, bech32.convertbits(url, 8, 5))

class LncliCommunicator:
	def __init__(self, network):
		self._network = network

	def get_uri(self):
		getinfo_cmd = ["lncli", "--network", self._network, "getinfo"]

		process = subprocess.Popen(getinfo_cmd, stdout=subprocess.PIPE)
		out, err = process.communicate()
		info = json.loads(out)

		return info["uris"][0]

	def open_channel(self, node_id, local_amt, remote_amt, is_private, host = None):
		cmd = ["lncli", "--network", self._network, "openchannel"]
		if host is not None:
			cmd.append("--connect")
			cmd.append(host)

		if is_private:
			cmd.append("--private")

		cmd += ["--remote_csv_delay", "144", "--sat_per_byte", "1", "--min_htlc_msat", "1000", node_id, str(local_amt), str(remote_amt)]

		process = subprocess.Popen(cmd)
		process.wait()

		return process.returncode == 0

class EclairCommunicator:
	def __init__(self, network):
		config_path = Path("~/.eclair/eclair.conf").expanduser()
		config = ConfigFactory.parse_file(config_path)
		self.password = config.get_string("eclair.api.password")

	def _query(self, command, data = {}):
		resp = requests.post("http://127.0.0.1:8080/" + command, data=data, auth=("eclair-cli", self.password))
		return resp

	def get_uri(self):
		info = self._query("getinfo").json()

		return info["nodeId"] + "@" + info["publicAddresses"][0]

	def open_channel(self, node_id, local_amt, remote_amt, private, host = None):
		if host is not None:
			conn = self._query("connect", { "uri": node_id + "@" + host })
			if conn.status_code != 200:
				return False

		req = {
				"nodeId": node_id,
				"fundingSatoshis": local_amt,
				"pushMsat": remote_amt * 1000,
				"fundingFeerateSatByte": 1,
				"channelFlags": 8 + int(not private),
		}
		return self._query("open", req).status_code == 200

BACKENDS = {
	"lncli": LncliCommunicator,
}

try:
	from pyhocon import ConfigFactory
	BACKENDS["eclair"] = EclairCommunicator

except ImportError:
	pass

class Server:
	def __init__(self, url_prefix, backend, www_root, auth_key):
		self._node_addr = backend.get_uri()
		self._url_prefix = url_prefix
		self._backend = backend
		self._offers = {}
		self.www_root = www_root
		self.auth_key = auth_key

	def create_lnurl(self, local_amt, push_amt):
		secret = secrets.token_hex(32)
		self._offers[secret] = (local_amt, push_amt)
		url = self._url_prefix + "/rq/0/" + secret
		return encode_lnurl(url.encode("utf-8"))

	def get_channel_data(self, secret):
		if secret in self._offers:
			offer = self._offers[secret]
			return {
				"uri": self._node_addr,
				"callback": self._url_prefix + "/rq/1/",
				"k1": secret,
				"capacity": offer[0],
				"push": offer[1],
				"htlcMinimumMsat": 1000,
				"cltvExpiryDelta": 144,
				"feeBaseMsat": 10,
				"feeProportionalMillionths": 500,
				"tag": "channelRequest"
			}
		else:
			return {
				"status": "ERROR",
				"reason": "Invalid secret"
			}

	def open_channel(self, secret, node_id, is_private):
		if secret in self._offers:
			offer = self._offers[secret]

			if self._backend.open_channel(node_id, offer[0], offer[1], is_private):
				del self._offers[secret]
				return {
					"status": "OK"
				}
			else:
				return {
					"status": "ERROR",
					"reason": "Failed to open a channel"
				}
		else:
			return {
				"status": "ERROR",
				"reason": "Invalid secret"
			}

def load_config(config_path):
	with open(config_path, "r") as config_file:
		return toml.load(config_file)

def usage():
	print("Usage: %s --conf CONFIG_FILE" % sys.argv[0])
	if "-h" in sys.argv or "--help" in sys.argv:
		sys.exit(0)
	else:
		sys.exit(1)

def main():
	global server
	if len(sys.argv) < 2 or "-h" in sys.argv or "--help" in sys.argv:
		usage()

	if sys.argv[1] == "--conf":
		if len(sys.argv) < 3:
			usage()
		else:
			config = load_config(sys.argv[2])
	else:
		fail("Error: unknown argument '%s'" % sys.argv[1])

	if "auth_key" not in config:
		fail("auth_key not specified in the config")

	auth_key = config["auth_key"]

	network = config.get("network", "mainnet")
	web_port = config.get("web_port", 8050)
	www_root = config.get("www_root", "./static")
	root_path = config.get("root_path", "/")
	if not root_path.startswith("/"):
		root_path = "/" + root_path

	if "backend" not in config:
		fail("backend not specified in the config, available backends: lncli, eclair")

	if config["backend"] not in BACKENDS:
		fail("Unknown backend %s, available backends: lncli, eclair" % config["backend"])

	backend = BACKENDS[config["backend"]](network)

	if "domain" not in config:
			fail("domain not specified in the config")
	domain = config["domain"]

	if  network == "mainnet" and not domain.startswith("http") and not domain.endswith(".onion"):
		fail("Insecure usage detected, you must use https or onion domain on mainnet")

	if not domain.startswith("http://") and not domain.startswith("https://"):
		fail("The domain must start with http:// or https://")

	server = Server(domain + root_path, backend, www_root, auth_key)

	run(host="localhost", port=web_port)

@route("/rq/0/<secret>")
def zeroth_request(secret):
	global server
	return server.get_channel_data(secret)

@route("/rq/1/")
def first_request():
	global server
	secret = request.query["k1"]
	node_id = request.query["remoteid"]
	is_private = request.query["private"]

	return server.open_channel(secret, node_id, is_private)

@route("/create/<key>/<local_amount:int>/<push_amount:int>")
def create(key, local_amount, push_amount):
	global server
	if key == server.auth_key:
		return server.create_lnurl(local_amount, push_amount)

@route("/admin/<file:path>")
def qrcode(file):
	global server
	return static_file(file, root=server.www_root)

@route("/admin")
def admin():
	global server
	return static_file("admin.html", root=server.www_root)
