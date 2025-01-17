"""
Created on 8 Aug 2021.

@author: Ben Lauret
"""

import platform
import logging
import struct
import binascii
import os
from datetime import datetime as datetime_, timedelta

from datetime import datetime, timedelta 
# now = datetime.now()
# date_time = now.strftime("%H:%M:%S, %m/%d/%Y ")  #mesg = date_time + "inside pyG5NetWorkManager(QObject):: da
import pickle

from PySide6.QtCore import QObject, Slot, Signal, QTimer

from PySide6.QtNetwork import QUdpSocket, QHostAddress, QAbstractSocket

from PySide6 import QtGui


class pyG5NetWorkManager(QObject):
    """pyG5NetWorkManager Object.

    This object listen on the XPlane multicast group
    and emit on the xpInstance signal the host address
    and port of the Xplane on the network

    Args:
        parent: Parent Widget

    Returns:
        self
    """

    drefUpdate = Signal(object)

    print("====== before init class pyG5NetWorkManager(QObject): network manager object in pyG5Main.py")
    def __init__(self, parent=None):
        """Object constructor.
            
        Args:
            parent: Parent Widget

        Returns:
            self
        """
        QObject.__init__(self, parent)
        print("==== __init__... class pyG5NetWorkManager(QObject): network manager object in pyG5Main.py")
 
        #print("==== inside class pyG5NetWork(QApplication): __init__()")
        self.logger = logging.getLogger(self.__class__.__name__)

        # Idle timer trigger reconnection
        self.idleTimerDuration = 10000
        self.idleTimer = QTimer()
        self.idleTimer.timeout.connect(self.reconnect)
        #
        self.HOST = "127.0.0.1"  # The server's hostname or IP address
        self.PORT = 65432  # The port used by the server
        self.Addr = QHostAddress(self.HOST)
        self.Port = self.PORT
        # Create local UDP socket
        self.udpSock = QUdpSocket(self)
        # manage stage change to send data request
        self.udpSock.stateChanged.connect(self.socketStateHandler)
        # manage received data
        self.udpSock.readyRead.connect(self.dataHandler)
        self.udpSock.connected.connect(self.connectedHandler)
        # bind the socket
        self.udpSock.bind(QHostAddress.LocalHost, self.Port)  
        #self.datagram, self.address, self.port = self.udpSock.readDatagram(1024)
        #print("==== inside class pyG5NetWorkManager(QApplication): datagram:", self.datagram, self.address, self.port)
        print("==== inside class pyG5NetWorkManager(QApplication): __init__() ,HOST, PORT ", self.HOST, self.PORT)

        self.xpHost = None
        # list the datarefs to request or reuse as retvalues 
        self.datarefs = [
            # ( dataref, frequency, unit, description, num decimals to display in formatted output )
            #0
            ("sim/cockpit2/autopilot/altitude_hold_ft",20,"ft","Altitude Hold",0,"_altitudeHold",),
            ("sim/cockpit2/autopilot/altitude_vnav_ft",20,"ft","Altitude VNAV",0,"_altitudeVNAV",),
            ("sim/cockpit2/radios/indicators/nav_src_ref",20,"enum","NAV source",0,"_navSrc",),
            ("sim/cockpit/autopilot/altitude",20,"feet","AP altitude selected",0,"_apAltitude",),
            ("sim/cockpit/autopilot/vertical_velocity",20,"fpm","NAV source",0,"_apVS",),
            ("sim/cockpit/autopilot/airspeed",20,"kt","AP air speed",0,"_apAirSpeed",),
            ("sim/cockpit/autopilot/autopilot_mode",20,"enum","AP mode",0,"_apMode",),
            ("sim/cockpit/autopilot/autopilot_state",20,"enum","AP state",0,"_apState",),
            ("sim/flightmodel/controls/parkbrake",1,"onoff","Parking brake set",0,"_parkBrake",),
            ("sim/cockpit/warnings/annunciators/fuel_quantity",1,"onoff","fuel selector",0,"_lowFuel",),
            ("sim/cockpit/warnings/annunciators/oil_pressure_low[0]",1,"onoff","fuel selector",0,"_oilPres",),
            #10
            ("sim/cockpit/warnings/annunciators/fuel_pressure_low[0]",1,"onoff","fuel selector",0,"_fuelPress",),
            ("sim/cockpit/warnings/annunciators/low_vacuum",1,"onoff","fuel selector",0,"_lowVacuum",),
            ("sim/cockpit/warnings/annunciators/low_voltage",1,"onoff","fuel selector",0,"_lowVolts",),
            ("sim/cockpit2/fuel/fuel_tank_selector",30,"onoff","fuel selector",0,"_fuelSel",),
            ("sim/cockpit2/engine/actuators/carb_heat_ratio[0]",30,"onoff","fuel pump on",0,"_carbheat",),
            ("sim/cockpit/engine/fuel_pump_on[0]",10,"onoff","fuel pump on",0,"_fuelpump",),
            ("sim/flightmodel/controls/elv_trim",30,"mode","Transponder mode",0,"_trims",),
            ("sim/flightmodel/controls/flaprat",30,"mode","Transponder mode",0,"_flaps",),
            ("sim/cockpit/radios/transponder_mode",5,"mode","Transponder mode",0,"_xpdrMode",),
            ("sim/cockpit/radios/transponder_code",5,"code","Transponder code",0,"_xpdrCode",),
            #20
            ("sim/cockpit/radios/gps_dme_dist_m",1,"Gs","GPS GS available",0,"_gpsdmedist",),
            ("sim/cockpit2/radios/indicators/fms_fpta_pilot",1,"Gs","GPS GS available",0,"_gpsvnavavailable",),
            (
                # int	n	enum	GPS CDI sensitivity: 0=OCN, 1=ENR, 2=TERM, 3=DPRT, 4=MAPR, 5=APR, 6=RNPAR, 7=LNAV, 8=LNAV+V, 9=L/VNAV, 10=LP, 11=LPV, 12=LP+V, 13=GLS
                "sim/cockpit/radios/gps_cdi_sensitivity",1,"index","GPS Horizontal Situation Indicator sensitivity mode",0,"_gpshsisens",),
            ("sim/cockpit/radios/gps_has_glideslope",1,"Gs","GPS GS available",0,"_gpsgsavailable",),
            ("sim/cockpit/radios/gps_gp_mtr_per_dot",1,"boolean","Avionics powered on",0,"_gpsvsens",),
            ("sim/cockpit/radios/nav_type[0]",1,"boolean","Avionics powered on",0,"_nav1type",),
            ("sim/cockpit/radios/nav_type[1]",1,"boolean","Avionics powered on",0,"_nav2type",),
            ("sim/cockpit/gps/destination_type",1,"boolean","Avionics powered on",0,"_gpstype",),
            ("sim/cockpit/electrical/avionics_on",1,"boolean","Avionics powered on",0,"_avionicson",),
            ("sim/cockpit/radios/nav1_vdef_dot",30,"Dots","NAV1 Vertical deviation in dots",0,"_nav1gs",),
            #30
            ("sim/cockpit/radios/nav2_vdef_dot",30,"Dots","NAV2 Vertical deviation in dots",0,"_nav2gs",),
            ("sim/cockpit/radios/gps_vdef_dot",30,"Dots","GPS Vertical deviation in dots",0,"_gpsgs",),
            ("sim/cockpit/radios/nav1_CDI",30,"Gs","Nav 1 GS available",0,"_nav1gsavailable",),
            ("sim/cockpit/radios/nav2_CDI",30,"Gs","Nav 2 GS available",0,"_nav2gsavailable",),
            ("sim/cockpit2/gauges/indicators/airspeed_acceleration_kts_sec_pilot",30,"Gs","GPS CRS",0,"_kiasDelta",),
            ("sim/cockpit2/radios/actuators/HSI_source_select_pilot",30,"°","GPS CRS",0,"_hsiSource",),
            ("sim/cockpit2/radios/indicators/nav1_flag_from_to_pilot",30,"°","NAV1 CRS",0,"_nav1fromto",),
            ("sim/cockpit2/radios/indicators/nav2_flag_from_to_pilot",30,"°","NAV2 CRS",0,"_nav2fromto",),
            ("sim/cockpit/radios/gps_fromto",30,"°","NAV2 CRS",0,"_gpsfromto",),
            ("sim/cockpit/radios/nav1_obs_degm",30,"°","NAV1 CRS",0,"_nav1crs",),
            #40
            ("sim/cockpit/radios/nav2_obs_degm",30,"°","NAV2 CRS",0,"_nav2crs",),
            ("sim/cockpit/radios/gps_course_degtm",30,"°","GPS CRS",0,"_gpscrs",),
            ("sim/cockpit/radios/gps_course_degtm",30,"°","GPS CRS",0,"_nav1dev",),
            ("sim/cockpit/radios/nav1_hdef_dot",30,"°","NAV1 VOR coursedeflection",0,"_nav1dft",),
            ("sim/cockpit/radios/nav2_hdef_dot",30,"°","NAV1 VOR course deflection",0,"_nav2dft",),
            ("sim/cockpit/radios/gps_hdef_dot",30,"°","GPS course deflection",0,"_gpsdft",),
            ("sim/flightmodel/position/magnetic_variation",30,"°","Ground track heading",0,"_magneticVariation",),
            ("sim/cockpit2/gauges/indicators/ground_track_mag_pilot",30,"°","Ground track heading",0,"_groundTrack",),
            ("sim/cockpit/autopilot/heading_mag",30,"°","Horizontal Situation Indicator bug",0,"_headingBug",),
            ("sim/weather/wind_direction_degt",30,"°","The effective direction of the wind at the plane's location",0,"_windDirection",),
            #50
            ("sim/weather/wind_speed_kt",30,"kt","The effective speed of the wind at the plane's location.",0,"_windSpeed",),
            ("sim/flightmodel/position/mag_psi",30,"°","Magnetic heading of the aircraft",0,"_magHeading",),
            ("sim/flightmodel/position/phi",30,"°","Roll of the aircraft",0,"_rollAngle",),
            ("sim/flightmodel/position/theta",30,"°","Pitch of the aircraft",0,"_pitchAngle",),
            ("sim/flightmodel/position/indicated_airspeed",30,"kt","Indicated airpseed",0,"_kias",),
            ("sim/cockpit2/gauges/indicators/true_airspeed_kts_pilot",30,"kt","Indicated airpseed",0,"_ktas",),
            ("sim/flightmodel/position/groundspeed",30,"kt","Indicated airpseed",0,"_gs",),
            ("sim/cockpit2/gauges/indicators/altitude_ft_pilot",30,"feet","Altitude",0,"_altitude",),
            ("sim/cockpit2/autopilot/altitude_dial_ft",30,"feet","Altitude",0,"_altitudeSel",),
            ("sim/cockpit2/gauges/actuators/barometer_setting_in_hg_pilot",30,"feet","Altimeter setting",0,"_alt_setting",),
            #60
            ("sim/physics/metric_press",1,"feet","Altimeter setting",0,"_alt_setting_metric",),
            ("sim/cockpit2/gauges/indicators/slip_deg",30,"°","Slip angle",0,"_slip",),
            ("sim/cockpit2/gauges/indicators/turn_rate_heading_deg_pilot",30,"°","Turn Rate",0,"_turnRate",),
            ("sim/flightmodel/position/vh_ind_fpm",30,"kt","Indicated airpseed",0,"_vh_ind_fpm",),
            ("sim/aircraft/view/acf_Vso",1,"kt","stall speed",0,"_vs0",),
            ("sim/aircraft/view/acf_Vs",1,"kt","stall in Landing configuration speed",0,"_vs",),
            ("sim/aircraft/view/acf_Vfe",1,"kt","flap extended speed",0,"_vfe",),
            ("sim/aircraft/view/acf_Vno",1,"kt","normal operation speed",0,"_vno",),
            ("sim/aircraft/view/acf_Vne",1,"kt","never exceed speed",0,"_vne",),
            #69
        ]

        '''orig code self.logger = logging.getLogger(self.__class__.__name__)

        # Idle timer trigger reconnection
        self.idleTimerDuration = 10000
        self.idleTimer = QTimer()
        self.idleTimer.timeout.connect(self.reconnect)

        # Create local UDP socket
        self.udpSock = QUdpSocket(self)

        # manage received data
        self.udpSock.readyRead.connect(self.dataHandler)

        # manage stage change to send data request
        self.udpSock.stateChanged.connect(self.socketStateHandler)

        # bind the socket
        self.udpSock.bind(
            QHostAddress.SpecialAddress.AnyIPv4, 0, QUdpSocket.BindFlag.ShareAddress
        )'''

    '''@Slot()
    def write_data_ref(self, path, data):
        """Idle timer expired. Trigger reconnection process."""
        cmd = b"DREF\x00"  # DREF command
        message = struct.pack("<5sf", cmd, data)
        message += bytes(path, "utf-8") + b"\x00"
        message += " ".encode("utf-8") * (509 - len(message))
        if self.xpHost:
            self.udpSock.writeDatagram(message, self.xpHost, self.xpPort)'''

    @Slot()
    def reconnect(self):
        """Idle timer expired. Trigger reconnection process."""
        self.logger.info("Connection Timeout expired")

        self.udpSock.close()
        #self.idleTimer.stop()

        # let the screensaver activate
        if platform.machine() in "aarch64":
            os.system("xset s on")
            os.system("xset s 1")

        #HOST = "127.0.0.1"  # The server's hostname or IP address
        #PORT = 65432  # The port used by the server
        self.Addr = QHostAddress(self.HOST)
        self.Port = self.PORT
        # Create local UDP socket
        self.udpSock = QUdpSocket(self)
        # manage stage change to send data request
        self.udpSock.stateChanged.connect(self.socketStateHandler)
        # manage received data
        self.udpSock.readyRead.connect(self.dataHandler)
        self.udpSock.connected.connect(self.connectedHandler)
        # bind the socket
        self.udpSock.bind(QHostAddress.LocalHost, self.Port)  
        # re start the idle timer
        self.idleTimer.start(self.idleTimerDuration)        
        print("==== inside reconnect(), new socket() created ,HOST, PORT ", self.HOST, self.PORT)


    ''' @Slot(QHostAddress, int)
    def xplaneConnect(self, addr, port):
        """Slot connecting triggering the connection to the XPlane."""
        self.listener.xpInstance.disconnect(self.xplaneConnect)
        self.listener.deleteLater()

        self.xpHost = addr
        self.xpPort = port

        self.logger.info("Request datatefs")
        # initiate connection
        for idx, dataref in enumerate(self.datarefs):
            cmd = b"RREF\x00"  # RREF command
            freq = dataref[1]
            ref = dataref[0].encode()
            message = struct.pack("<5sii400s", cmd, freq, idx, ref)
            self.logger.info("Request datatefs: {}".format(ref))
            assert len(message) == 413
            self.udpSock.writeDatagram(message, addr, port)
            end = datetime_.now() + timedelta(milliseconds=20)
            while datetime_.now() < end:
                QtGui.QGuiApplication.processEvents()

        # start the idle timer
        self.idleTimer.start(self.idleTimerDuration)

        # now we can inhibit the screensaver
        if platform.machine() in "aarch64":
            os.system("xset s reset")
            os.system("xset s off")'''

    @Slot(QAbstractSocket.SocketState)
    def socketStateHandler(self):
        """Socket State handler."""
        self.logger.info("pyG5NetWorkManager().socketStateHandler start {}".format(self.udpSock.state()))
        # socket bind ok
        if self.udpSock.state() == QAbstractSocket.SocketState.BoundState:
            print("====inside pyG5Network.py socketStateHandler BoundState")
            self.logger.info("====inside pyG5Network.py socketStateHandler BoundState")
            self.logger.info("pyG5NetWorkManager().socketStateHandler() self.udpSock.state() == QAbstractSocket.BoundState ")
            # listener ?
            '''# instantiate the multicast listener
            self.listener = pyG5MulticastListener(self)

            # connect the multicast listenner to the connect function
            self.listener.xpInstance.connect(self.xplaneConnect)'''
        #unconnected state
        elif self.udpSock.state() == QAbstractSocket.SocketState.UnconnectedState:
            # socket got disconnected issue reconnection
            self.udpSock.bind(QHostAddress.AnyIPv4, 0, QUdpSocket.BindFlag.ShareAddress)
            self.logger.info("pyG5NetWorkManager().socketStateHandler self.udpSock.state() = QAbstractSocket.UnconnectedState ")
        #connected state
        elif self.udpSock.state() == QAbstractSocket.ConnectedState:
            print("socket udp connected")
        #
        '''"""Socket State handler."""
        self.logger.info("socketStateHandler: {}".format(self.udpSock.state()))

        if self.udpSock.state() == QAbstractSocket.SocketState.BoundState:
            self.logger.info("Started Multicast listenner")
            # instantiate the multicast listener
            self.listener = pyG5MulticastListener(self)

            # connect the multicast listenner to the connect function
            self.listener.xpInstance.connect(self.xplaneConnect)

        elif self.udpSock.state() == QAbstractSocket.SocketState.UnconnectedState:
            # socket got disconnected issue reconnection
            self.udpSock.bind(
                QHostAddress.SpecialAddress.AnyIPv4, 0, QUdpSocket.BindFlag.ShareAddress
            )'''
    @Slot()
    def connectedHandler(self): 
        print("connectedHandler...")
        self.logger.debug("udp connected: {}".format(self.udpSock.state()))

    @Slot()
    def dataHandler(self): 
        #print("\n***** inside pyG5NetworkMAV.dataHandler() *****")
        #print("Response: ", self.udpSock.readAll())
        # timestamp date_time
        now = datetime.now()
        date_time = now.strftime("%H:%M:%S, %m/%d/%Y ")  #mesg = date_time + "inside pyG5NetWorkManager(QObject):: dataHandler())" #self.logger.info(mesg)   
        # data received restart the idle timer
        self.idleTimer.start(self.idleTimerDuration)
        #print("datahandler waiting for data")
        while self.udpSock.hasPendingDatagrams(): 
            data = self.udpSock.receiveDatagram() 
            #print("\rdatahandler()Rcvd: ", len(data.data()), end="") #print(".",) ("\rComplete: ", i, "%", end="")
            if (len(data.data()) < 5):
                return
            data_dict = pickle.loads(data.data())
            #print("\rdatahandler()Rcvd: len:", len(data.data())) #," ", data_dict, end="") #print(".",) ("\rComplete: ", i, "%", end="")
            # if data_dict has entries then emit log message
            mesg = date_time + "Received data_dict= " + str(data_dict)
            #self.logger.info(mesg)   #for k, v in data_dict.items(): print(k, v)
            #
            retvalues = {} # create (for now empty) dict to emit as signal later
            numvalues = 1 
            idx = 0
            for i in range(0, numvalues):
                #
                idx = 52 # _magHeading #23 old # _magHeading  
                value = 0
                try:
                    val = data_dict["hdg"] 
                    #print("\ndronekit val hdg/100",val/100)
                    value = float(val.replace("'","")) #data_dict["'roll'"] #float(datarefs[idx][4])      
                    #print("\ndronekit value hdg/100",value/100)
                    retvalues[idx] = (
                        value/100,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                        )             
                except:
                    pass
                try:
                    val = data_dict["heading_deg"] 
                    #print("\nmavsdk val heading_deg", val)
                    #value = float(val.replace("'","")) #data_dict["'roll'"] #float(datarefs[idx][4])      
                    #print("\nmavsdk value heading_deg", value) 
                    retvalues[idx] = (
                        val,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                        )             
                except:
                    pass
                    ''''try:
                        val = data_dict["'hdg'"] # 10.0 to test  #print("inside class pyG5NetWorkManager(QObject): dataHandler() val = data_dict['roll'] =", type(val), " , ", val )
                        value = float(val.replace("'","")) #data_dict["'roll'"] #float(datarefs[idx][4]) 
                        #print("inside class pyG5NetWorkManager(QObject): dataHandler() value = data_dict['roll'] =", type(value), " , ", str(value) )
                    except:
                        pass #self.logger.info("error inside class pyG5NetWorkManager(QObject): dataHandler() Error getting data_dict['hdg'] ")
                    #self.logger.info("error inside class pyG5NetWorkManager(QObject): dataHandler() Error getting data_dict['hdg'] ")   '''               
                    
                idx = 53 #24 # _rollAngle
                value = 0
                try:
                    val = data_dict["roll"] 
                    value = float(val.replace("'","")) 
                    #print("\ndronekit val roll", value)
                    retvalues[idx] = (
                        value*100,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                        )
                except:
                    pass #bypass
                try:
                    val = data_dict["roll_deg"] 
                    #value = float(val.replace("'","")) #data_dict["'roll'"] #float(datarefs[idx][4])
                    #print("\nmavsdk val roll_deg", val)
                    retvalues[idx] = (
                        val,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                        )
                except:
                    pass #bypass
                    ''''try:
                        val = data_dict["'roll'"] # 10.0 to test  #print("inside class pyG5NetWorkManager(QObject): dataHandler() val = data_dict['roll'] =", type(val), " , ", val )
                        value = float(val.replace("'","")) #data_dict["'roll'"] #float(datarefs[idx][4])
                        #print("inside class pyG5NetWorkManager(QObject): dataHandler() value = data_dict['roll'] =", type(value), " , ", str(value) )
                    except:
                        pass #self.logger.info("error inside class pyG5NetWorkManager(QObject): dataHandler() Error getting data_dict['roll'] ")
                    #self.logger.info("error inside class pyG5NetWorkManager(QObject): dataHandler() Error getting data_dict['roll'] ")'''
                    
                idx = 54 #25 # _pitchAngle
                value = 0
                try:
                    val = data_dict["pitch"] 
                    value = float(val.replace("'",""))
                    #print("\ndronekit val pitch", value)
                    retvalues[idx] = (
                        value*100,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                        )
                except:
                    pass #bypass
                try:
                    val = data_dict["pitch_deg"] 
                    #value = float(val.replace("'","")) 
                    #print("\nmavsdk val pitch_deg", val)
                    retvalues[idx] = (
                        val,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                        )
                except:
                    pass #bypass
                    '''try:
                        val = data_dict["'pitch'"] # 10.0 to test  #print("inside class pyG5NetWorkManager(QObject): dataHandler() val = data_dict['roll'] =", type(val), " , ", val )
                        value = float(val.replace("'","")) #data_dict["'roll'"] #float(datarefs[idx][4])
                        #print("inside class pyG5NetWorkManager(QObject): dataHandler() value = data_dict['pitch'] =", type(value), " , ", str(value) )
                    except:
                        pass #self.logger.info("error inside class pyG5NetWorkManager(QObject): dataHandler() Error getting data_dict['pitch'] ")
                    #self.logger.info("error inside class pyG5NetWorkManager(QObject): dataHandler() Error getting data_dict['pitch'] ")'''
                #    
                #
                idx = 58 #29 # _altitude
                value = 0
                try: # DRONEKIT SITL or ARDDUPILOT
                    val = data_dict["alt"]*3.28084 # convert to feet # self.data_dict["relative_altitude_m"]*3.28084
                    #value = float(val.replace("'","")) 
                    #print("\ndronekit val alt", val)
                    retvalues[idx] = (
                        val/10,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                        )
                except:
                    pass #bypass
                try:  # MAVSDK PX4
                    val = data_dict["relative_altitude_m"]*3.28084   # old ["absolute_altitude_m"]
                    #value = float(val.replace("'","")) 
                    #print("\nmavsdk val alt", val)
                    retvalues[idx] = (
                        val,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                        )
                except:
                    pass #bypass
                    ''''try:
                        val = data_dict["'alt'"] # 10.0 to test  #print("inside class pyG5NetWorkManager(QObject): dataHandler() val = data_dict['roll'] =", type(val), " , ", val )
                        value = float(val.replace("'","")) #data_dict["'roll'"] #float(datarefs[idx][4])
                        #print("inside class pyG5NetWorkManager(QObject): dataHandler() value = data_dict['roll'] =", type(value), " , ", str(value) )
                    except:
                        try:
                            val = data_dict["altitude_local"] #print("inside class pyG5NetWorkManager(QObject): dataHandler() val = data_dict['roll'] =", type(val), " , ", val )
                            value = float(val.replace("'","")) #data_dict["'roll'"] #float(datarefs[idx][4])
                            #print("inside class pyG5NetWorkManager(QObject): dataHandler() value = data_dict['roll'] =", type(value), " , ", str(value) )
                        except:
                            pass #self.logger.info("error inside class pyG5NetWorkManager(QObject): dataHandler() Error getting data_dict['alt'] ")
                    #self.logger.info("error inside class pyG5NetWorkManager(QObject): dataHandler() Error getting data_dict['alt'] ")'''
                    
            # end packing dict to pickle and send to pyG5 as emit signal    
            #print("$$$$$$$ sending drefUpdate signal...retvalues: ", retvalues)
            self.drefUpdate.emit(retvalues)
            break
        '''"""dataHandler."""
        # data received restart the idle timer
        self.idleTimer.start(self.idleTimerDuration)

        while self.udpSock.hasPendingDatagrams():
            datagram = self.udpSock.receiveDatagram()
            data = datagram.data()
            retvalues = {}
            # Read the Header "RREFO".
            header = data[0:5]
            if header != b"RREF,":
                self.logger.error("Unknown packet: ", binascii.hexlify(data))
            else:
                # We get 8 bytes for every dataref sent:
                #    An integer for idx and the float value.
                values = data[5:]
                lenvalue = 8
                numvalues = int(len(values) / lenvalue)
                idx = 0
                value = 0
                for i in range(0, numvalues):
                    singledata = data[(5 + lenvalue * i) : (5 + lenvalue * (i + 1))]
                    (idx, value) = struct.unpack("<if", singledata.data())
                    retvalues[idx] = (
                        value,
                        self.datarefs[idx][1],
                        self.datarefs[idx][0],
                        self.datarefs[idx][5],
                    )
                    # if idx == 0:
                    #     print("idx: {}, value: {}".format(idx, value))
                drefUpdate.emit(retvalues)'''

'''
class pyG5MulticastListener(QObject):
    """pyG5MulticastListener Object.

    This object listen on the XPlane multicast group
    and emit on the xpInstance signal the host address
    and port of the Xplane on the network

    Args:
        parent: Parent Widget

    Returns:
        self
    """

    xpInstance = Signal(QHostAddress, int)

    def __init__(self, parent=None):
        """Object constructor.

        Args:
            parent: Parent Widget

        Returns:
            self
        """
        QObject.__init__(self, parent)

        self.logger = logging.getLogger(self.__class__.__name__)

        self.XPAddr = QHostAddress("239.255.1.1")
        self.XPPort = 49707

        # create the socket
        self.udpSock = QUdpSocket(self)

        self.udpSock.stateChanged.connect(self.stateChangedSlot)
        self.udpSock.readyRead.connect(self.udpData)
        self.udpSock.connected.connect(self.connectedSlot)
        self.udpSock.bind(
            QHostAddress.SpecialAddress.AnyIPv4,
            self.XPPort,
            QUdpSocket.BindFlag.ShareAddress,
        )
        if not self.udpSock.joinMulticastGroup(self.XPAddr):
            logging.error("Failed to join multicast group")

    @Slot(QAbstractSocket.SocketState)
    def stateChangedSlot(self, state):
        """stateChangedSlot."""
        self.logger.debug("Sock new state: {}".format(state))

    @Slot()
    def connectedSlot(self):
        """connectedSlot."""
        self.logger.debug("udp connected: {}".format(self.udpSock.state()))

    @Slot()
    def udpData(self):
        """udpData."""
        while self.udpSock.hasPendingDatagrams():
            datagram = self.udpSock.receiveDatagram()
            if "BECN" in str(datagram.data())[2:6]:
                self.xpInstance.emit(
                    datagram.senderAddress(),
                    int.from_bytes(bytes(datagram.data())[19:21], byteorder="little"),
                )
                self.udpSock.leaveMulticastGroup(self.XPAddr)
                self.udpSock.close()
                break'''
