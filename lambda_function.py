import logging
import time
import json
import uuid

# OAuth library for sending requests to device cloud
from requests_oauthlib import OAuth2Session

# Imports for v3 validation
#from validation import validate_message

# Setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(request, context):

    try:

        logger.info("Directive:")
        logger.info(json.dumps(request, indent=4, sort_keys=True))
        
        version = get_directive_version(request)
        logger.info("Version: " + version)

        if version == "3":
            response = v3_handle_message(request)

        else:
            response = v2_handle_message(request)

        logger.info("Response:")
        logger.info(json.dumps(response, indent=4, sort_keys=True))

# Uncomment when import of validation library works
#        if version == "3":
#            logger.info("Validate v3 response")
#            validate_message(request, response)

        return response

    except ValueError as error:
        logger.error(error)
        raise

def get_directive_version(request):
    try:
        return request["directive"]["header"]["payloadVersion"]
    except:
        try:
            return request["header"]["payloadVersion"]
        except:
            return "-1"

def v3_handle_message(request):

    if request["directive"]["header"]["namespace"] == "Alexa.Discovery":
        return v3_handle_discovery(request)
    
    elif request["directive"]["header"]["namespace"] == "Alexa.PowerController":
        return v3_handle_power_control(request)
    
    elif request["directive"]["header"]["namespace"] == "Alexa.Authorization":
        return v3_handle_authorization(request)

def v3_handle_discovery(request):

    client = oAuth_client(request["directive"]["payload"]["scope"]["token"])

    # Request the power devices, and build response from this
    endpoints = []    
    for device in list_power_devices(client):
        logger.info("Discovered " + device["name"] + " (" + device["description"] + "), id=" + device["id"])
        endpoints.append({
            "endpointId": device["id"],
            "manufacturerName": "Intuso",
            "friendlyName": device["name"],
            "description": device["description"],
            "displayCategories": ["LIGHT"], # todo check the classes/abilities of the device
            "cookie": {},
            "capabilities": [{
                "type": "AlexaInterface",
                "interface": "Alexa.EndpointHealth",
                "version": "3",
                "properties": {
                    "supported":[
                        { "name":"connectivity" }
                    ],
                    "proactivelyReported": True,
                    "retrievable": True
                }
            },{
                "type": "AlexaInterface",
                "interface": "Alexa",
                "version": "3"
            },{
                "type": "AlexaInterface",
                "interface": "Alexa.PowerController",
                "version": "3",
                "properties": {
                    "supported": [
                        # { "name": "powerState" } todo Add in when we start reporting state directly to Alexa
                    ],
                    "proactivelyReported": False, # todo Set to true when we start reporting state directly to Alexa
                    "retrievable": False # todo Set to true when we start reporting state directly to Alexa
                }
            }]
        })

    return {
        "event": {
            "header": {
                "namespace": "Alexa.Discovery",
                "name": "Discover.Response",
                "payloadVersion": "3",
                "messageId": get_uuid()
            },
            "payload": {
                "endpoints": endpoints
            }
        }
    }

def v3_handle_power_control(request):

    device_id = request["directive"]["endpoint"]["endpointId"]
    client = oAuth_client(request["directive"]["endpoint"]["scope"]["token"])

    if request["directive"]["header"]["name"] == "TurnOn":
        turn_on(client, device_id)
        value = "ON"
    elif request["directive"]["header"]["name"] == "TurnOff":
        turn_off(client, device_id)
        value = "OFF"

    response = {
        "context": {
            "properties": [
                {
                    "namespace": "Alexa.PowerController",
                    "name": "powerState",
                    "value": value,
                    "timeOfSample": get_utc_timestamp(),
                    "uncertaintyInMilliseconds": 500
                }
            ]
        },
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": "Response",
                "payloadVersion": "3",
                "messageId": get_uuid(),
                "correlationToken": request["directive"]["header"]["correlationToken"]
            },
            "endpoint": {
                "scope": {
                    "type": "BearerToken",
                    "token": "access-token-from-Amazon"
                },
                "endpointId": request["directive"]["endpoint"]["endpointId"]
            },
            "payload": {}
        }
    }
    return response

def v3_handle_authorization(request): # todo is this for setting the token for calling back?

    client = oAuth_client(request["directive"]["payload"]["scope"]["token"])

    if request["directive"]["header"]["name"] == "AcceptGrant":
        response = {
            "event": {
                "header": {
                    "namespace": "Alexa.Authorization",
                    "name": "AcceptGrant.Response",
                    "payloadVersion": "3",
                    "messageId": "5f8a426e-01e4-4cc9-8b79-65f8bd0fd8a4"
                },
                "payload": {}
            }
        }
        return response

def v2_handle_message(request):

    client = oAuth_client(request["payload"]["accessToken"])

    if request["header"]["namespace"] == "Alexa.ConnectedHome.Discovery":
        return v2_handle_discovery(client, request)

    elif request["header"]["namespace"] == "Alexa.ConnectedHome.Control":
        return v2_handle_control(client, request)

def v2_handle_discovery(client, request):

    # Request the power devices, and build response from this
    devices = []    
    for device in list_power_devices(client):
        logger.info("Discovered " + device["name"] + " (" + device["description"] + "), id=" + device["id"])
        devices.append({
            "applianceId": device["id"],
            "manufacturerName": "Intuso",
            "modelName": "Device",
            "version": "1",
            "friendlyName": device["name"],
            "friendlyDescription": device["description"],
            "isReachable": True,
            "actions": [
                "turnOn",
                "turnOff"
            ],
            "additionalApplianceDetails":{}
        })
    
    return {
        "header": {
            "namespace": "Alexa.ConnectedHome.Discovery",
            "name": "DiscoverAppliancesResponse",
            "payloadVersion": "2",
            "messageId": get_uuid()
        },
        "payload": {
            "discoveredAppliances": devices
        }
    }

def v2_handle_control(client, request):

    payload = {}
    header = {
        "namespace": "Alexa.ConnectedHome.Control",
        "payloadVersion": "2",
        "messageId": get_uuid()
    }

    device_id = request["payload"]["appliance"]["applianceId"]

    if request["header"]["name"] == "TurnOnRequest":
        turn_on(client, device_id)
        header["name"] = "TurnOnConfirmation"
    elif request["header"]["name"] == "TurnOffRequest":
        turn_off(client, device_id)
        header["name"] = "TurnOffConfirmation"
    
    return {
        "header": header,
        "payload": payload
    }

# Util functions
def get_uuid():
    return str(uuid.uuid4())

def get_utc_timestamp(seconds=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S.00Z", time.gmtime(seconds))

def oAuth_client(access_token):
    return OAuth2Session(client_id="d2a28431-78b6-41b0-ac4a-9405742c0b55", token={"access_token":access_token, "token_type":"Bearer"})

def list_power_devices(client):
    logger.info("Discovering devices")
    response = client.get("https://intuso.com/housemate/api/server/1.0/util/ability/power?limit=-1")
    return json.loads(response.text)["elements"]

def turn_on(client, device_id):
    logger.info("Turning on " + device_id)
    client.post("https://intuso.com/housemate/api/server/1.0/util/ability/power/" + device_id + "/on")

def turn_off(client, device_id):
    logger.info("Turning off " + device_id)
    client.post("https://intuso.com/housemate/api/server/1.0/util/ability/power/" + device_id + "/off")

# Example taken from https://github.com/alexa/alexa-smarthome/blob/master/sample_lambda/python/lambda.py

""" V2 sample appliances
SAMPLE_APPLIANCES = [
    {
        "applianceId": "endpoint-001",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart Switch",
        "version": "1",
        "friendlyName": "Switch",
        "friendlyDescription": "001 Switch that can only be turned on/off",
        "isReachable": True,
        "actions": [
            "turnOn",
            "turnOff"
        ],
        "additionalApplianceDetails": {
            "detail1": "For simplicity, this is the only appliance",
            "detail2": "that has some values in the additionalApplianceDetails"
        }
    },
    {
        "applianceId": "endpoint-002",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart Light",
        "version": "1",
        "friendlyName": "Light",
        "friendlyDescription": "002 Light that is dimmable and can change color and color temperature",
        "isReachable": True,
        "actions": [
            "turnOn",
            "turnOff",
            "setPercentage",
            "incrementPercentage",
            "decrementPercentage",
            "setColor",
            "setColorTemperature",
            "incrementColorTemperature",
            "decrementColorTemperature"
        ],
        "additionalApplianceDetails": {}
    },
    {
        "applianceId": "endpoint-003",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart White Light",
        "version": "1",
        "friendlyName": "White Light",
        "friendlyDescription": "003 Light that is dimmable and can change color temperature only",
        "isReachable": True,
        "actions": [
            "turnOn",
            "turnOff",
            "setPercentage",
            "incrementPercentage",
            "decrementPercentage",
            "setColorTemperature",
            "incrementColorTemperature",
            "decrementColorTemperature"
        ],
        "additionalApplianceDetails": {}
    },
    {
        "applianceId": "endpoint-004",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart Thermostat",
        "version": "1",
        "friendlyName": "Thermostat",
        "friendlyDescription": "004 Thermostat that can change and query temperatures",
        "isReachable": True,
        "actions": [
            "setTargetTemperature",
            "incrementTargetTemperature",
            "decrementTargetTemperature",
            "getTargetTemperature",
            "getTemperatureReading"
        ],
        "additionalApplianceDetails": {}
    },
    {
        "applianceId": "endpoint-004-1",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart Thermostat Dual",
        "version": "1",
        "friendlyName": "Living Room Thermostat",
        "friendlyDescription": "004-1 Thermostat that can change and query temperatures, supports dual setpoints",
        "isReachable": True,
        "actions": [
            "setTargetTemperature",
            "incrementTargetTemperature",
            "decrementTargetTemperature",
            "getTargetTemperature",
            "getTemperatureReading"
        ],
        "additionalApplianceDetails": {}
    },
    {
        "applianceId": "endpoint-005",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart Lock",
        "version": "1",
        "friendlyName": "Lock",
        "friendlyDescription": "005 Lock that can be locked and can query lock state",
        "isReachable": True,
        "actions": [
            "setLockState",
            "getLockState"
        ],
        "additionalApplianceDetails": {}
    },
    {
        "applianceId": "endpoint-006",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart Scene",
        "version": "1",
        "friendlyName": "Good Night Scene",
        "friendlyDescription": "006 Scene that can only be turned on",
        "isReachable": True,
        "actions": [
            "turnOn"
        ],
        "additionalApplianceDetails": {}
    },
    {
        "applianceId": "endpoint-007",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart Activity",
        "version": "1",
        "friendlyName": "Watch TV",
        "friendlyDescription": "007 Activity that runs sequentially that can be turned on and off",
        "isReachable": True,
        "actions": [
            "turnOn",
            "turnOff"
            ],
        "additionalApplianceDetails": {}
    },
    {
        "applianceId": "endpoint-008",
        "manufacturerName": "Sample Manufacturer",
        "modelName": "Smart Camera",
        "version": "1",
        "friendlyName": "Baby Camera",
        "friendlyDescription": "008 Camera that streams from an RSTP source",
        "isReachable": True,
        "actions": [
            "retrieveCameraStreamUri"
            ],
        "additionalApplianceDetails": {}
    }
]
"""