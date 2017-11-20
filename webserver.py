# author : Rajiv Basavaraj Patil rapa9011@colorado.edu
# name   : Webserver.py
# purpose: Implementation of webserver using socket programming
# date   : 11/20/2017
# version: 1.0.0

import threading
import sys
import os
import logging
import socket

HTTP_RESPONSE = {
    200: 'OK',
    400: '<HTML><HEAD><TITLE>400 Bad Request</TITLE></HEAD><body>400 Bad request: Server unable to process the request<br>Please check the request header and try again<br></BODY></HTML>',
    404: '<HTML><HEAD><TITLE>404 File Not Found</TITLE></HEAD><body>404 File Not Found: Unable to find the requested file<br>please check the address and try again<br></BODY></HTML>',
    501: '<HTML><HEAD><TITLE>501 Not Implemented</TITLE></HEAD><body>501 Not Implemented: Method not Supported<br>The requested method is not supported by the browser<br></BODY></HTML>',
    500: '<HTML><HEAD><TITLE>500 Internal Error</TITLE></HEAD><body>500 Internal Error: Internal Server Error<br>Error at server during page processing<br></BODY></HTML>'
}

HTTP_RESPONSE1 = {
    200: 'OK',
    400: 'Bad Request',
    404: 'Not Found',
    501: 'Not Implemented',
    500: 'Internal error'
}

'''
The class Server does the following:
1) Open the socket
2)binds the socket
3)listens, which tells the socket library that we want it to queue up as many as 5 connect requests
4) accept request
5)Start a thread for executing the request
6)Recv the request that the browser (client) sends
7) serves the Request
8) closes the
 connection
'''


class Server():
    def __init__(self, configDetails):
        self.host = ''
        self.port = 8000  # TO BE READ FROM THE CONFIG FILE LATER
        self.threads = []
        self.configDetails = configDetails
        self.create_socket()

    def create_socket(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create an INET, STREAMing socket
            sock.bind((self.host, self.port))  # bind the socket to a host, and a port
            sock.listen(200)  # queue up as many as 5 connect requests
            logger.info('Serving HTTP on port %s ...' % self.port)
            self.sock = sock
            self.accept_req()  # call accept_req()
        except socket.error as message:
            if sock:
                sock.close()
            logger.info("Could not open socket: " + str(message))
            sys.exit(1)

    def accept_req(self):
        id = 0
        # check and turn on TCP Keepalive
        x = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
        if (x == 0):
            x = self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        else:
            print('Socket Keepalive already on')
        try:
            self.sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 10000, 2000))
            while 1:
                conn, addr = self.sock.accept()  # accept Request
                if conn:
                    id = id + 1
                    logger.info("Connection Accepted")
                    logger.info("New connection is setup")
                    thr_multiple = Multiple(conn, addr, id, self.configDetails)
                    thr_multiple.setDaemon(True)
                    logger.info("Thread " + str(id) + " is now created")
                    for each in self.threads:
                        if each.conn == conn:
                            print("There is a match, we got the old guy")
                    self.threads.append(thr_multiple)
                    # print("Current request source :")
                    # print(conn)
                    thr_multiple.start()

                for elements in self.threads:
                    # Check if threads have encountered Socket Timeout
                    if elements.checktimeout():
                        # If the timeouts have encountered, then join those threads only
                        logger.info("Thread " + str(elements.getID()) + " is being killed")
                        elements.join()
                        # remove those items from the list
                        self.threads.remove(elements)


        except(KeyboardInterrupt, SystemExit):
            #print("Keyboard interrupt occured")
            logger.info("Keyboard Interrupt Generated")
            logger.info("Program Now Exits")
            sys.exit()


'''
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

PAGE HANDLING CLASS
    -THIS CLASS IS DESIGNED TO HANDLE ANY REQUESTS AND QUERIES RELATED TO 
    WEBPAGE ACCESS. THIS INCLUDES REQUESTS, RESPONSES AND ERROR HANDLING

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
'''


class PageHandling():
    def __init__(self, request, addr, dict):
        self.request = request
        self.addr = addr
        self.dict = dict

    def ErrorMessage(self, err_code):
        self.request.send(HTTP_RESPONSE[err_code].encode())

    def ResponseHeader(self, response, content, size, type):
        VerStr = 'HTTP/' + self.dict['version']
        R_ID = str(response) + ' ' + HTTP_RESPONSE1[response]
        self.request.send((VerStr + ' ' + R_ID + '\r\n').encode())
        # if content is not 'NULL':
        if response == 200:
            self.request.send(
                (('Content-Type: ' + content + '; charset=utf-8 \r\n').encode()))  # + str(content)).encode())
        if size is not 'NULL':
            self.request.send(('Content-Length: ' + str(size) + '\r\n').encode())
        if self.dict['ConnStatus'].strip() == 'keep-alive':
            self.request.send(('Keep-Alive: timeout=' + str(self.dict['KeepaliveTime']) + ', max=1000\r\n').encode())
            self.request.send('Connection: Keep-Alive\r\n'.encode())
        else:
            self.request.send('Connection: Close\r\n'.encode())
        self.request.send('\r\n'.encode())

    def POSTResponse(self, path):
        self.ResponseHeader(400, 'NULL', len(HTTP_RESPONSE[400]), 'NULL')
        self.ErrorMessage(400)

    def SendResponse(self, path):
        try:
            fh = open(path, 'rb')
            fsize = os.path.getsize(path)
            self.ResponseHeader(200, self.dict['ContentType'], fsize, 'NULL')
            BytesSent = 0
            while BytesSent < fsize:
                lines = fh.read(1024)
                self.request.send(lines)
                BytesSent = BytesSent + 1024
            fh.close()
            logger.info("Page Successfully Transmitted")
        except:
            print("Error occured")
            logger.info("There was an interruption in sending the Data")

    def Fetch_WebPage(self, path):
        if not os.path.isfile(path):
            logger.info(str(path) + " not found in the Root Directory")
            self.ResponseHeader(404, "PAGE NOT FOUND", len(HTTP_RESPONSE[404]), 'NULL')
            self.ErrorMessage(404)
            return
        logger.info("Preparing response header to transfer the webpage details")
        type = path[1:].split('.')
        ContentType = type[1]
        if ContentType in self.dict.keys():
            self.dict['ContentType'] = self.dict[ContentType]

        self.SendResponse(path)

    def ReqCompatibility(self):
        if self.dict['request'] not in ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'CONNECT'):
            logger.error("Invalid Method found in HTTP request")
            return False
        if self.dict['version'] == '1.0' and self.dict['request'] in ('PUT', 'DELETE', 'TRACE', 'CONNECT'):
            logger.error("HTTP/1.1 request " + self.dict['request'] + " is not supported in HTTP/1.0")
            return False
        if self.dict['version'] == '1.0' and self.dict['ConnStatus'] == 'keep-alive' and self.dict['request'] in (
        'GET', 'HEAD', 'POST'):
            # Reset the Connection Status
            self.dict['ConnStatus'] = 'Closed'
            return True

        if (self.dict['version'] == '1.0' or self.dict['version'] == '1.1') and self.dict['request'] in (
        'GET', 'HEAD', 'POST'):
            return True


'''
###########################################################################

MULTIPLE CLASS
    -THIS CLASS IS USED TO MANAGE THREADING FOR DIFFERENT SOCKETS

###########################################################################

'''


class Multiple(threading.Thread):
    def __init__(self, request, addr, id, dict):
        threading.Thread.__init__(self)
        print("client connected at ", addr)
        self.conn = request
        self.addr = addr
        self.size = 65535
        self.id = id
        self.dict = dict
        self.timeoutFlag = False

    def run(self):
        logger.info("Invoking thread: " + str(self.id))
        self.conn.settimeout(int(self.dict['KeepaliveTime']))
        try:
            while True:
                data = ''
                while not data:
                    data = self.conn.recv(4096)
                data = data.decode()
                #print("REQ " + data)
                lines = data.split('\r\n')
                request, path, version = lines[0].split()
                for each in lines:
                    if "Connection" in each:
                        ConnStatus = each.split(":")
                        print(ConnStatus)
                        self.dict['ConnStatus'] = str(ConnStatus[1]).strip()

                #Check for the Connection Status
                if 'ConnStatus' not in self.dict.keys():
                    self.dict['ConnStatus'] = "Close"
                self.dict['request'] = request
                versiontype = version.split('/')
                self.dict['version'] = versiontype[1]

                #Initiate the Page Handling Class
                RQ_Handler = PageHandling(self.conn, self.addr, self.dict)
                if (RQ_Handler.ReqCompatibility() == False):
                    RQ_Handler.ResponseHeader(400, 'NULL', len(HTTP_RESPONSE[400]), 'NULL')
                    RQ_Handler.ErrorMessage(400)
                    continue

                if (request == 'GET'):
                    # check if no path is given, then we need to load the default page from configuration file
                    if path != '/':
                        RQ_Handler.Fetch_WebPage(path[1:])
                    else:
                        # fetch the default page from configuration file
                        defPath = ConfigCheck.getDefaultPage()
                        if defPath == 'NULL':
                            logger.error("Default Page cannot be found")
                        else:
                            RQ_Handler.Fetch_WebPage(defPath)

                elif (request == 'POST'):
                    print("POST request")
                    each = data.split('\r\n')
                    print(each[-1])
                    datatoWrite = each[-1]
                    total_size = os.path.getsize('basic.html') + len(datatoWrite)
                    RQ_Handler.ResponseHeader(200, 'NULL', total_size, 'NULL')
                    fh = open('basic.html', 'r')
                    lines = fh.readlines()
                    for every in lines:
                        self.conn.send(every.encode())
                        print(every)
                        if '<body>' in every:
                            print("got the slot")
                            self.conn.send(('<h1>' + datatoWrite + '</h1>').encode())
                    fh.close()
                else:

                    RQ_Handler.ResponseHeader(501, 'NULL', len(HTTP_RESPONSE[404]), 'NULL')
                    RQ_Handler.ErrorMessage(501)

                print("Completed processing of thread :" + str(self.id))
                self.conn.settimeout(int(self.dict['KeepaliveTime']))

        except socket.timeout:
            logger.error("Socket Timeout Occured for Thread " + str(self.id))
            self.conn.close()
            self.timeoutFlag = True
        except:
            logger.error("Client is closing connection")
            self.conn.close()
            self.timeoutFlag = True

    def checktimeout(self):
        return self.timeoutFlag

    def getID(self):
        return self.id


'''
###########################################################################

CONFIGURATION MANAGEMENT CLASS
    -THIS CLASS IS USED TO MANAGE PRECHECKS FOR CONFIGURATION OF SERVER BERFORE 
    IT CAN BE STARTED

###########################################################################

'''

class ConfigManagement():
    def __init__(self):
        self.config = {
        }
        self.getConfigDetails()

    def getConfigDetails(self):
        if (not os.path.isfile("ws.conf")):
            logger.info("Configuration File Missing")
            return False
        logger.info("Configuration File found : " + os.getcwd() + "\ws.conf")
        logging.info("Fetching Default Page Path")
        with open("ws.conf", 'r') as fh:
            lines = fh.readlines()
            for each in lines:
                formatdetails = each.strip()
                if each[0] == '#' or formatdetails == '':
                    continue
                if 'ContentType' in each:
                    (dummy, key, value) = each.split()
                else:
                    (key, value) = each.split()
                self.config[key] = value
        logger.info("Successfully extracted the configuration details")

    def getDefaultPage(self):
        try:
            filePath = self.config['DocumentRoot'] + '\\basic.html'
            if os.path.isfile(filePath):
                logging.info("Default Page Path is found: " + self.config['DocumentRoot'])
                return filePath
            else:
                logging.error("Default Page Path not found")
                return 'NULL'
        except:
            logger.error("Directory index missing in the configuration file")
            return 'NULL'

    def preCheckList(self, logger):
        # check the configuration file before start
        if (not os.path.isfile("ws.conf")):
            logger.info("Configuration File Missing")
            return False
        logger.info("Configuration File found : " + os.getcwd() + "\ws.conf")
        with open("ws.conf", 'r') as fh:
            lines = fh.readlines()
            for each in lines:
                if 'ListenPort' in each:
                    PortNum = each.split()
                    try:
                        if int(PortNum[1]) < 1024:
                            logger.error("Port number less than 1024 found in configuration")
                            return False
                    except:
                        logger.error("Invalid Port Number found in the configuration file.")
                        return False
                    logger.info("Port Number Found : " + PortNum[1] + " in configuration file")
        return True

'''
***********************************************************************

MAIN FUNCTION

***********************************************************************
'''

if __name__ == '__main__':
    # Initialize logger
    logger = logging.getLogger()  # Check for the Name of the logger Handler
    # Remove the old Configuration File
    if os.path.isfile('WebServer.log'):
        os.remove('WebServer.log')
    # Initialize the logger
    hdlr = logging.FileHandler(os.getcwd() + '/WebServer.log')
    formatter = logging.Formatter('%(asctime)s \t %(levelname)s \t%(message)s')  #
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    logger.info('Logging begins')
    # Do some Precheck before the webserver can be started
    ConfigCheck = ConfigManagement()
    logger.info("Checking for Valid Configurations")
    FileExists = ConfigCheck.preCheckList(logger)

    if not FileExists:
        logger.info("Program now Exits")
        sys.exit()

    #Start the Server Instance
    server = Server(ConfigCheck.config)

