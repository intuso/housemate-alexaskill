from requests_oauthlib import OAuth2Session
import json

def lambda_handler(event, context):

    access_token = event['payload']['accessToken']
    client = OAuth2Session(client_id="d2a28431-78b6-41b0-ac4a-9405742c0b55", token={"access_token":access_token, "token_type":"Bearer"})

    if event['header']['namespace'] == 'Alexa.ConnectedHome.Discovery':
        return handleDiscovery(client, event)

    elif event['header']['namespace'] == 'Alexa.ConnectedHome.Control':
        return handleControl(client, event)

def handleDiscovery(client, event):

    message_id = event['header']['messageId']

    payload = ''
    header = {
        "messageId": message_id,
        "name": "DiscoverAppliancesResponse",
        "namespace": "Alexa.ConnectedHome.Discovery",
        "payloadVersion": "2"
    }

    if event['header']['name'] == 'DiscoverAppliancesRequest':
        response = client.get("https://intuso.com/housemate/api/server/1.0/power?limit=-1")
        parsed = json.loads(response.text)
        devices = []
        for device in parsed["elements"]:
            devices.append({
                "actions": [
                    "turnOn",
                    "turnOff"
                ],
                "additionalApplianceDetails":{},
                "applianceId":device["id"].encode('ascii','ignore'),
                "friendlyDescription":device["description"].encode('ascii','ignore'),
                "friendlyName":device["name"].encode('ascii','ignore'),
                "isReachable":True,
                "manufacturerName":"intuso",
                "modelName":"switch",
                "version":"1.0"
            })
        payload = {"discoveredAppliances":devices}
    return { 'header': header, 'payload': payload}

def handleControl(client, event):

    message_id = event['header']['messageId']

    payload = {}
    header = {
        "namespace":"Alexa.ConnectedHome.Control",
        "payloadVersion":"2",
        "messageId": message_id
    }

    device_id = event['payload']['appliance']['applianceId']

    if event['header']['name'] == 'TurnOnRequest':
        client.post("https://intuso.com/housemate/api/server/1.0/power/" + device_id + "/on")
        header["name"] = "TurnOnConfirmation"
    elif event['header']['name'] == 'TurnOffRequest':
        client.post("https://intuso.com/housemate/api/server/1.0/power/" + device_id + "/off")
        header["name"] = "TurnOffConfirmation"

    return { 'header': header, 'payload': payload }

# list_event = {
#     "header": {
#         "payloadVersion": "2",
#         "namespace": "Alexa.ConnectedHome.Discovery",
#         "name": "DiscoverAppliancesRequest",
#         "messageId":"1"
#     },
#     "payload": {
#         "accessToken": "fe6c98a52497b817cde57ad45b2d7c50"
#     }
# }
#
# on_event = {
#     "header": {
#         "payloadVersion": "2",
#         "namespace": "Alexa.ConnectedHome.Control",
#         "name": "TurnOnRequest",
#         "messageId":"1"
#     },
#     "payload": {
#         "accessToken": "fe6c98a52497b817cde57ad45b2d7c50",
#         "appliance": {
#             "additionalApplianceDetails": {},
#             "applianceId": "812576b6-c073-4118-8ef0-d04b47ff30cb"
#         },
#     }
# }
#
# off_event = {
#     "header": {
#         "payloadVersion": "2",
#         "namespace": "Alexa.ConnectedHome.Control",
#         "name": "TurnOnRequest",
#         "messageId":"1"
#     },
#     "payload": {
#         "accessToken": "fe6c98a52497b817cde57ad45b2d7c50",
#         "appliance": {
#             "additionalApplianceDetails": {},
#             "applianceId": "812576b6-c073-4118-8ef0-d04b47ff30cb"
#         },
#     }
# }
#
# print("list -> " + str(lambda_handler(list_event, {})))
# print("on -> " + str(lambda_handler(on_event, {})))
# print("off -> " + str(lambda_handler(off_event, {})))

