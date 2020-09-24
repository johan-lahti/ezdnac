from ezdnac.excepts import *
from ezdnac.utils import *
import requests
import json
import re
import os


# When initialized, populate device parameters:
# Retreive switchId based on serialnumber
class Device():
    def __init__(self, dnac, **kwargs):
        self.dnac = dnac
        self.id = None
        self.hostname = None
        self.serialNumber = None
        self.state = None
        self.deploymentId = None
        self.executionId = None
        self.taskId = None

        PNPdevice = None
        INVdevice = None

        if 'id' in kwargs:
            self.id = kwargs['id']
            self.initMethod = 'id'
        elif 'sn' in kwargs:
            self.serialNumber = kwargs['sn']
            self.initMethod = 'sn'
        elif 'hostname' in kwargs:
            self.hostname = kwargs['hostname']
            self.initMethod = 'hostname'

        # Make sure at least one argument is set to find the device
        if self.id is None and self.serialNumber is None and self.hostname is None:
            raise ezDNACError(
                'No device argment found. Enter hostname, id or sn')

        # if init method is id, the device must be in inventory.
        if self.initMethod in 'id':

            self.state = "Provisioned"
            INVdevice = self.dnac.getInventoryDevies(id=self.id)
            if INVdevice == None:
                raise ezDNACError('device not found by id')

        # if init method is hostname, the device must be in inventory.
        elif self.initMethod == 'hostname':

            INVdevice = self.dnac.getInventoryDevies(hostname=self.hostname)
            if INVdevice == None:
                raise ezDNACError('device not found by hostname')

        # if method is sn, the device can be either in inventory or pnp, have to try both
        elif self.initMethod == 'sn':

            # Try inventory:
            INVdevice = self.dnac.getInventoryDevies(sn=self.serialNumber)

            if INVdevice == None:
                PNPdevice = self.dnac.getPnpDevices(sn=self.serialNumber)

                if PNPdevice == None:
                    raise ezDNACError('device not found by serial Number')

        if INVdevice is not None:
            self.state = "Provisioned"
            self.id = INVdevice['id']
            self.platform = INVdevice['platformId']
            for key, value in INVdevice.items():
                setattr(self, key, value)


        # If device is found in pnp inventory, populate it
        if PNPdevice is not None:
            self.id = PNPdevice['id']
            for key, value in PNPdevice['deviceInfo'].items():
                setattr(self, key, value)


            # If stack, check first switch
            if 'stackInfo' in PNPdevice['deviceInfo']:
                if 'stackMemberList' in PNPdevice['deviceInfo']['stackInfo']:
                    if len(PNPdevice['deviceInfo']['stackInfo']['stackMemberList']) > 1:

                        self.hostname = PNPdevice['deviceInfo']['name']
                        self.id = PNPdevice['id']
                        self.softwareType = PNPdevice['deviceInfo']['agentType']
                        self.state = PNPdevice['deviceInfo']['state']
                        self.platform = PNPdevice['deviceInfo']['pid']

                        # Some attributes is picked from first switch in stack.
                        stack1 = PNPdevice['deviceInfo']['stackInfo']['stackMemberList'][0]
                        self.softwareVersion = stack1['softwareVersion']

                else:
                    self.id = PNPdevice['id']
                    self.state = PNPdevice['deviceInfo']['state']
                    self.hostname = PNPdevice['deviceInfo']['name']
                    self.platform = PNPdevice['deviceInfo']['pid']
                    self.softwareVersion = PNPdevice['deviceInfo']['imageVersion']
                    self.softwareType = PNPdevice['deviceInfo']['agentType']


                try:
                    httpHeaders = PNPdevice['deviceInfo']['httpHeaders']
                    for header in httpHeaders:
                        if header['key'] == 'clientAddress':
                            self.ip = header['value']
                except:
                    pass

    @property
    def collectionStatus(self):
        endpoint = f"network-device/{self.id}"
        response = restcall('GET', self.dnac, endpoint).get('response')
        self._collectionStatus = response.get('collectionStatus')
        return self._collectionStatus


    @collectionStatus.setter
    def collectionStatus(self, string):
        self._collectionStatus = string


    def updateAttributes(self):
        endpoint = f"network-device/{self.id}"
        response = restcall('GET', self.dnac, endpoint).get('response')

        for key, value in response.items():
            setattr(self, key, value)

        try:
            self.serialNumber = response['serialNumber'].split(',')
            self.ip = response['managementIpAddress']
            self.platform = response['platformId']
            self.softwareVersion = response['softwareVersion']
        except:
            pass

        return None

    def getInterfaces(self):
        endpoint = f"interface/network-device/{self.id}"
        data = restcall('GET', self.dnac, endpoint)
        return data

    def getTopology(self):
        ret = []
        endpoint = "topology/physical-topology/"
        data = restcall('GET', self.dnac, endpoint)
        connections = {}
        links = []
        for link in data['response']['links']:
            try:
                connections['sourcenode'] = link['source']
                connections['remotenode'] = link['target']
                connections['sourceif'] = link['startPortName']
                connections['remoteif'] = link['endPortName']
                links.append(dict(connections))
            except:
                pass
        ret = links
        return ret

    def getConnections(self):
        ret = []
        endpoint = "topology/physical-topology/"
        data = restcall('GET', self.dnac, endpoint)
        connections = {}
        links = []
        for link in data['response']['links']:
            if link['source'] == self.id:
                print(link)
                connections['remotenode'] = link['target']
                connections['remoteif'] = link['endPortName']
                connections['localif'] = link['startPortName']
                links.append(dict(connections))
            elif link['target'] == self.id:
                connections['remotenode'] = link['source']
                connections['remoteif'] = link['startPortName']
                connections['localif'] = link['endPortName']
                links.append(dict(connections))
        ret = links
        return ret

    def deployTemplate(self, template):
        """
        Inputs:
        template (obj) ezdnac template object

        Returns data (dict):
        {
        'deploymetId': id(str),   if error occurs, deploymentId returns None.
        'message': (str)
        }
        """
        data = {}
        data['deploymentId'] = None
        data['message'] = None
        endpoint = "template-programmer/template/deploy"

        payload = {
            "forcePushTemplate": template.force,
            "templateId": template.id,
            "targetInfo": [
                {
                    "id": self.id,
                    "type": "MANAGED_DEVICE_UUID",
                    "params": template.params
                }
            ]}

        response = restcall('POST', self.dnac, endpoint, jsondata=payload)


        # If error occurs, no id
        if 'response' in response and 'errorCode' in response['response']:
            data['deploymentId'] = None
            data['message'] = response['response']
            data['deployed'] = False
            return data

        # This is how the id should be found, if the API wasnt broken.
        if 'deploymentId' in response and type(response['deploymentId']) is int:
            data['deploymentId'] = response['deploymentId']
            data['message'] = 'Id found in response'
            data['deployed'] = True
            self.deploymentId = response
            return data

        # This is how it is solved with regex instead.
        if 'deploymentId' in response and type(response['deploymentId']) is not int:
            data['message'] = 'Id found with regex, broken response'

            # Testing if id is in response:
            resultRegex = (re.findall(r'Template Deployemnt Id.*', response['deploymentId']))

            if len(resultRegex) is not 0:
                Id = str(resultRegex).strip("['Template Deployemnt Id: ]")
                if resultRegex is not None:
                    data['deploymentId'] = Id
                    data['deployed'] = True
                    self.deploymentId = data
                    return data

        # If template was not deployed
        if re.match(r'.*already deployed with same params.*', response['deploymentId']):
            data['deploymentId'] = None
            data['deployed'] = True
            data['message'] = 'Same version already deployed with same params'
        else:
            data['deploymentId'] = None
            data['deployed'] = False
            data['message'] = response

        return data


    def deployTemplateStatus(self, **kwargs):
        if 'id' in kwargs:
            self.deploymentId = kwargs['id']

        if self.deploymentId == None:
            return None

        if self.deploymentId['deploymentId'] == None:
            return self.deploymentId['message']
        else:
            endpoint = f"template-programmer/template/deploy/status/{self.deploymentId['deploymentId']}"
            data = restcall('GET', self.dnac, endpoint)

            if 'status' in data:
                return data['status']
            else:
                return data

    def deployTemplateReport(self, **kwargs):
        if 'id' in kwargs:
            self.deploymentId = kwargs['id']

        endpoint = f"template-programmer/template/deploy/status/{self.deploymentId['deploymentId']}"
        response = restcall('GET', self.dnac, endpoint)
        return response

    def findNextPortchannel(self):
        endpoint = f"interface/network-device/{self.id}"
        response = restcall('GET', self.dnac, endpoint)

        existing_ids = []
        for interface in response['response']:
            if re.match(r'Port-channel.*', str(interface['portName'])):
                intf = int(str(interface['portName']).strip("'Port-channel"))
                existing_ids.append(intf)

        for i in range(1, 49):
            if (i) not in existing_ids:
                next_id = i
                break
        return next_id

    def assignToSite(self, siteId):
        baseurl = "/dna/system/api/v1/"
        endpoint = f"site/{siteId}/device"
        payload = {
            "device": [
                {
                    "ip": self.ip
                }
            ]
        }

        response = restcall('POST', self.dnac, endpoint, baseurl=baseurl, jsondata=payload)
        try:
            self.executionId = response['executionId']
        except:
            pass
        return response

    def getNeighbors(self):
        connections = self.getConnections()
        neighbors = []
        for link in connections:
            if link['remotenode'] in neighbors:
                continue
            else:
                neighbors.append(link['remotenode'])
        return neighbors

    # return every interface connected to us from specific neighbor

    def getNeighborIfs(self, neighbor):
        connections = self.getConnections()
        interfaces = []
        for link in connections:
            if link['remotenode'] == neighbor:
                interfaces.append(link['remoteif'])
        return interfaces

    def getModules(self):
        endpoint = f'network-device/module?deviceId={self.id}'
        modules = restcall('GET', self.dnac, endpoint)

        self.modules = modules.get('response')
        switches = []
        for module in self.modules:
            name = module['name']
            switch = str((re.findall(r'Switch \d', name))).strip("[']")
            switches.append(switch)
        self.stackcount = len((set(switches)))

        return modules

    def claimDevice(self, siteId, **kwargs):
        endpoint = "onboarding/pnp-device/site-claim"
        configParams = []

        if 'payload' in kwargs:
            payload = kwargs['payload']

        elif 'template' in kwargs:
            template = kwargs['template']
            for key, value in template.params.items():
                param = {"key": key, "value": value}
                configParams.append(param)

            payload = {
                "siteId": siteId,
                "deviceId": self.id,
                "type": "Default",
                "imageInfo": {
                    "imageId": "None",
                    "skip": True
                },
                "configInfo": {
                    "saveToStartUp": True,
                    "connLossRollBack": True,
                    "configId": template.id,
                    "configParameters": configParams}
            }
        else:
            payload = {
                "siteId": siteId,
                "deviceId": self.id,
                "type": "Default",
                "imageInfo": {"imageId": "None", "skip": "true"},
                "configInfo": {"configId": "", "configParameters": []}
            }

        print(json.dumps(payload, indent=4))
        data = restcall('POST', self.dnac, endpoint, jsondata=payload)
        print(data)
        try:
            self.executionId = response['executionId']
        except:
            pass
        return data

    def sync(self):
        baseurl = '/dna/intent/api/v1/'
        endpoint = 'network-device/sync'
        payload = f'["{self.id}"]\n\n'
        data = restcall('PUT', self.dnac, endpoint, data=payload, baseurl=baseurl)

        self.taskId = data.get('response').get('taskId')
        return data

    def getTaskStatus(self, **kwargs):
        if 'id' in kwargs:
            taskId = kwargs['id']
        elif self.taskId is not None:
            taskId = self.taskId
        else:
            return None

        endpoint = f'task/{self.taskId}'
        data = restcall('GET', self.dnac, endpoint)
        return data

    def getExecutionStatus(self, **kwargs):
        if 'id' in kwargs:
            executionId = kwargs['id']
        elif self.executionId is not None:
            executionId = self.executionId
        else:
            return None

        baseurl = '/dna/platform/management/business-api/v1/'
        endpoint = f'execution-status/{self.executionId}'
        data = restcall('GET', self.dnac, endpoint, baseurl=baseurl)
        return data
