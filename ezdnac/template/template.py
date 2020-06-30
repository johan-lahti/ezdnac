from ezdnac.excepts import *
from ezdnac.utils import *
import ezdnac.dnac
import requests
import json
import re
import os



class Template():
    def __init__(self, dnac, **kwargs):
        """
        Creates a new Template obj.

        Input parameters
        :dna(ezdnac DnaC object)
        :kwargs['all'] = Boolean # If True, all templates are choosen
        :kwargs['id'] = STRING # id of the template to work with
        :kwargs['name'] = STRING # name of the template
        """
        self.id = None
        self.name = None
        self.all = False
        self.data = None
        self.params = None
        self.authToken = dnac.authToken
        self.dnacIP = dnac.ip
        self.port = dnac.port
        self.uid = dnac.uid
        self.pw = dnac.pw
        self.dnac = dnac

        if 'all' in kwargs:
            if kwargs['all'] is True:
                self.all = True
                self.data = self.getTemplates()

        elif 'id' in kwargs:
            self.id = kwargs['id']
            allTemplates = self.getTemplates()
            for project in allTemplates:
                for template in project['templates']:
                    if template['id'] == kwargs['id']:
                        self.data = self.getTemplateInfo(self.id)
                        self.name = template['name']

        elif 'name' in kwargs:
            self.name = kwargs['name']
            allTemplates = self.getTemplates()
            for project in allTemplates:
                for template in project['templates']:
                    if template['name'] == kwargs['name']:
                        self.id = template['id']
                        self.data = self.getTemplateInfo(self.id)

    def setParams(self, params):
        if type(params) is dict:
            self.params = params
        else:
            raise ezDNACError('Template parameters has to be of type dict.')
        return "Params set"

    def getTemplates(self):
        endpoint = "template-programmer/project"
        data = restcall('GET', self.dnac, endpoint)
        return data

    def getTemplateId(self, templateName):
        data = self.getTemplates()
        for projects in data:
            for templates in projects['templates']:
                try:
                    if templates['name'] == templateName:
                        return (templates['id'])
                except:
                    return None

    def getTemplateInfo(self, templateId):
        endpoint = "template-programmer/template/" + templateId
        data = restcall('GET', self.dnac, endpoint)
        return data

    def newVersion(self):
        endpoint = "template-programmer/template/version"
        payload = {
            'comments': 'Updated with EZDNAC',
            'templateId': self.id
        }
        data = restcall('POST', self.dnac, endpoint, jsondata=payload)

    def pullTemplates(self, **kwargs):
        path = ""
        projectName = None
        try:
            projectName = kwargs['project']
        except:
            pass
        try:
            path = kwargs['path']
        except:
            pass

        endpoint = "template-programmer/project"
        data = restcall('GET', self.dnac, endpoint)

        templateslist = []
        # Get the id of interesting templates:
        for projects in data:
            if projectName is not None:
                if (projects['name']) == projectName:
                    for template in projects['templates']:
                        templates = {}
                        templates['id'] = template['id']
                        templateslist.append(templates)
            else:
                for template in projects['templates']:
                    templates = {}
                    templates['id'] = template['id']
                    templateslist.append(templates)

        for template in templateslist:
            url = "https://" + self.ip + ":" + self.port + baseurl + \
                "template-programmer/template/" + template['id']

            templateEndpoint = "template-programmer/template/" + template['id']
            templateData = restcall('GET', self.dnac, templateEndpoint)

            # Create template path folder if not exists already
            if not os.path.exists(path):
                os.mkdir(path)

            # Creates one subfolder per template, containting separate files for parameters and content
            templatePath = path + templateData['name']
            if not os.path.exists(templatePath):
                os.mkdir(templatePath)

            # Create a file for the actual content:
            contentsFilename = templatePath + "/" + \
                templateData['name'] + "_contents.txt"
            with open(contentsFilename, 'w') as out:
                templateParams = templateData['templateContent']
                out.write(str(templateParams))

            # Create a file for all parameters:
            paramsFilename = templatePath + "/" + \
                templateData['name'] + "_params.json"
            with open(paramsFilename, 'w') as out:
                templateParams = templateData
                if 'templateContent' in templateParams:
                    del templateParams['templateContent']
                out.write(str(json.dumps(templateParams, indent=4)))

        if path == "":
            path = "local folder"
        if projectName is not None:
            return "All templates in project: " + projectName + " are synced to: " + path
        else:
            return "All templates in all projects are synced to: " + path

    def pushTemplates(self, **kwargs):
        path = ""
        try:
            path = kwargs['path']
        except:
            pass

        # Createa a reference dict for each templatefolder:
        templatesList = []
        listdir = os.listdir(path)
        folders = []
        for obj in listdir:
            if not re.match(r"^\.", obj):
                folders.append(obj)

        for folder in folders:
            templateDict = {"name": folder}
            templateName = folder
            templatePath = path + folder

            for file in os.listdir(path + folder):
                if re.match(r'.*_params.json', file):
                    templateDict['paramsFile'] = templatePath + "/" + file

                if re.match(r'.*_contents.txt', file):
                    templateDict['contentsFile'] = templatePath + "/" + file

            templatesList.append(templateDict)
        print(templateDict)

        # Firest check if template already exists:
        for template in templatesList:

            # Opening both files
            # Content from the _content.json file:
            templateContents = str(open(template['contentsFile'], 'r').read())

            # All parameters from the params file:
            with open(template['paramsFile']) as templateData:
                templateFile = json.load(templateData)
                templateName = templateFile['name']
                projectName = templateFile['projectName']

                # Check whats already existing, based on project/template tree name
                endpoint = "template-programmer/project/"

                data = restcall('GET', self.dnac, endpoint)

                templateExists = False
                projectExists = False
                for project in data:
                    if project['name'] == projectName:
                        projectExists = True
                        projectId = project['id']
                        print ("Project exists: " +
                               projectName + " - " + projectId)

                        for templates in project['templates']:
                            if templates['name'] == templateName:
                                templateId = templates['id']
                                templateExists = True
                                print ("Template exists: " +
                                       templateName + " - " + templateId)

                if projectExists == False:
                    print ("Creating missing project: " + projectName)
                    endpoint = "template-programmer/project"

                    payload = {
                        "name": projectName,
                    }

                    data = restcall('POST', self.dnac, endpoint, json=payload)

                    # Since the project didn't exist, we need to fetch it's new id.
                    taskId = data['response']['taskId']
                    datafromtask = self.taskStatus(id=taskId)
                    projectId = datafromtask['data']

                if templateExists == False:
                    print ("Creating missing template: " + templateName)

                    endpoint = "template-programmer/project/" + projectId + "/template"
                    payload = templateFile
                    # Remove keys, making the payload suitable for new-creation of template. Hence removing id etc.
                    if 'id' in payload:
                        del payload['id']
                    for param in payload['templateParams']:
                        if 'id' in param:
                            del param['id']

                    for param in payload['templateParams']:
                        if 'selection' in param:
                            del param['selection']

                    payload['templateContent'] = str(templateContents)

                    data = restcall('POST', self.dnac, endpoint, json=payload)
                    
                    try:
                        self.taskId = data['response']['taskId']
                    except:
                        self.taskId = None

                if templateExists == True:
                    # Since the template exists, PUT the file from directory to make sure the active template is same version.
                    print ("Template " + templateName +
                           " already exists, versioning and updating.")

                    headers = {
                        'x-auth-token': self.authToken,
                        'Content-Type': 'application/json',
                    }

                    versionEndpoint = "template-programmer/template/version"
                    versionPayload = {
                        'comments': 'Updated with EZDNAC',
                        'templateId': templateId
                    }

                    restcall('POST', self.dnac, versionEndpoint, json=versionPayload)

                    endpoint = "template-programmer/template/"
                    payload = templateFile
                    payload['id'] = templateId

                    for params in payload['templateParams']:
                        del params['id']

                    for param in payload['templateParams']:
                        if 'selection' in param:
                            del param['selection']

                    payload['templateContent'] = templateContents

                    data = restcall('PUT', self.dnac, endpoint, json=payload)

