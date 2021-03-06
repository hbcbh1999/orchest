import asyncio
import json
import os
import requests
import subprocess

from flask import request
from flask_restplus import Namespace, Resource, fields

from app.utils import shutdown_jupyter_server


api = Namespace('servers', description='Start and stop Jupyter servers')

# Server information to connect to JupyterLab instance.
server = api.model('Server', {
    'url': fields.String(
        required=True,
        description='URL of the server'),
    'hostname': fields.String(
        required=True,
        default='localhost',
        description='Hostname'),
    'port': fields.Integer(
        required=True,
        description='Port to access the server'),
    'secure': fields.Boolean(
        required=True,
        description='Any extra security measures'),
    'base_url': fields.String(
        required=True,
        default='/',
        description='Base URL'),
    'token': fields.String(
        required=True,
        description='Token for authentication'),
    'notebook_dir': fields.String(
        required=True,
        description='Directory of the server'),
    'password': fields.Boolean(
        required=True,
        description='Password if one is set'),
    'pid': fields.Integer(
        required=True,
        description='PID'),
})

# follows Jupyter command line parameters
jupyter_config = api.model('Jupyter Config', {
    'gateway-url': fields.String(
        required=True,
        description='URL of the EG'),
    'NotebookApp.base_url': fields.String(
        required=True,
        description='Base URL of Jupyter notebook'),
})

message = api.model('Message', {
    'message': fields.String(
        required=True,
        description='Message clarifying response')
})


@api.route('/')
class Server(Resource):
    abs_path = os.path.dirname(os.path.abspath(__file__))
    connection_file = os.path.join(abs_path, '..', 'tmp', 'server_info.json')

    # TODO: 404 is not the correct error code, yet the flask-restplus
    #       framework does not allow multiple @api.response for the same
    #       error code.
    @api.doc('get_launch')
    @api.response(model=message, code=404, description='Server not found')
    @api.response(model=server, code=200, description='Server fetched')
    def get(self):
        """Fetch the server information if it is running."""
        if not os.path.exists(self.connection_file):
            return api.marshal(fields=message,
                               data={'message': 'No running server'}), 404

        with open(self.connection_file, 'r') as f:
            server_info = json.load(f)

        return api.marshal(fields=server, data=server_info), 200

    # TODO: super stricly there can only be one running server at any
    #       moment. Thus another POST request when a server is already
    #       running should return an error code.
    @api.doc('start_server')
    @api.expect(jupyter_config)
    @api.marshal_with(server, code=201, description='Server started')
    def post(self):
        """Starts a Jupyter server."""
        # Use the flask "request context".
        post_data = request.get_json()

        # Parse arguments to pass to the subprocess. The "args" should
        # be a sequence of program arguments. Because if it is a string,
        # then the interpretation is platform-dependent (see python
        # docs).
        start_script = os.path.join(self.abs_path, '..', 'core', 'start_server.py')
        args = ['python', '-u', start_script]
        args.extend([
            f'--{arg}={value}'
            for arg, value in post_data.items()
        ])

        # Need to start a new event loop to start a subprocess.
        asyncio.set_event_loop(asyncio.new_event_loop())

        # Start a Jupyter server within a subprocess.  The "-u" option
        # is to avoid buffering. Since it will be a long running
        # process, we want output whilst the program is running such
        # that we know when and if the server did successfully start.
        proc = subprocess.Popen(args=args, stdout=subprocess.PIPE)

        # Wait for the server to be booted, it will write a message to
        # stdout once successful.
        _ = proc.stdout.readline()

        # Get the information to connect to the server.
        with open(self.connection_file, 'r') as f:
            server_info = json.load(f)

        # TODO: return 404 in case it did not work!

        return server_info, 201

    @api.doc('shutdown_server')
    @api.response(200, 'Server stopped')
    @api.response(404, 'Server not found')
    def delete(self):
        """Shuts down running Jupyter server."""
        success = shutdown_jupyter_server(self.connection_file)

        if not success:
            return {'message': 'No running server'}, 404

        # There no longer is a running server, so clean up the file.
        os.remove(self.connection_file)

        return {'message': 'Server shutdown was successful'}, 200
