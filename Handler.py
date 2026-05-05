msfs_mode = 1

# -----
# User configuration section
# -----

# Replace the <CID> with your VATSIM CID in just numbers. Ensure that you put in just the number. For example, "userVarVATSIMCID = 1880962". '<CID>' by default.
userVarVATSIMCID = '<CID>'

# If you encounter issues, set this to True. The line should look like: "verboseLog = True". This enables very detailed logging in couatl.log. False by default.
verboseLog = False

# Show the status of chocks and the gate number. False by default.
showChockandGate = False

# Show the data on payloads, such as passengers, cargo, and fuel. False by default.
showPaxCargoFuel = False

# -----
# End of user configuration. Do not modify anything below this line unless you know what you are doing.
# -----

# At least one of these need to be online on VATSIM for the handler to ping the CDM API. 
airportATC = ['ESSA_ATIS', 'ESSA_D_ATIS', 'ESSA_A_ATIS', 'ESSA_DEL', 'ESSA_GND', 'ESSA_TWR', 'ESSA_E_APP', 'ESSA_W_APP'] 

# How long one VDGS page should last
vdgsDuration = 10000

# How many VDGS pages there are by default, not accounting for the chock and gate or the pax, cargo, and fuel pages
vdgsPages = 3 

# This is the prefix for all log messages in couatl.log. These are off by default to prevent flooding the log file, instruct your users to enable it above if they want to see the logs as a troubleshooting measure.
handlerID = "Linas's ESSA Handler log: "

varVATSIMCID = None
handlerCycleRunning = False

# Input is a string of 4 numbers in HHMM or 6 numbers in HHMMSS, output is a time object that takes real time and adds the hhmmss time to it
def hhmmssToObj(hhmmss):
    irlTimeInt = time.time()
    irlTimeObj = time.gmtime(irlTimeInt)
    irlIntBase = irlTimeInt - irlTimeObj[3] * 3600 - irlTimeObj[4] * 60 - irlTimeObj[5]
    hh = int(hhmmss[0:2])
    mm = int(hhmmss[2:4])
    ss = hhmmss[4:6]

    # ss can be omitted, this is the fallback to ensure that if it is not present, nothing breaks
    if ss == '':
        ss = 0
    else:
        ss = int(ss)
    
    tgtInt = irlIntBase + hh * 3600 + mm * 60 + ss

    # If it detects that target time is more than 12 hours before current time, it adds 24 hours to the integer to have it cross over into the next day. This is a fallback to ensure that people who load in at 2355Z with a TOBT of 0015Z, for instance, don't have "+23 hours" as their TTD but rather have the correct "-20 minutes"
    if (irlTimeInt - tgtInt) > 43200:
        if verboseLog:
            print(f'{handlerID}Adding 24 hours to time to account for day rollover.')
        tgtInt = tgtInt + (24 * 3600)

    if verboseLog:
        print(f'{handlerID}hhmmssToObj function variables:\nInput Time String: {hhmmss}\nCurrent IRL Time (int): {irlTimeInt}\nCurrent IRL Time (obj): {irlTimeObj}\nIRL Time Base (int): {irlIntBase}\nTarget Time (int): {tgtInt}\nTarget Time (obj): {time.gmtime(tgtInt)}')

    return time.gmtime(tgtInt)

# Technically this isn't necessary but having it makes life easier
def splitTime(timeObj):
    return f'{timeObj[3]:02d}{timeObj[4]:02d}'

def compareTime(ttc, isGameTime):
    # ttc - Time to compare
    timeRef = 0

    if isGameTime:
        timeInt0AD = executeCalculatorCode('(E:ABSOLUTE TIME, seconds)') # Gets the absolute time in seconds since 1/1/1 AD

        timeRef = timeInt0AD - 62135596800 # - 62135596800 converts the time from seconds since 1/1/1 AD to seconds since 1/1/1970
        
    else:
        timeRef = time.time()

    ttcCompared = calendar.timegm(ttc) - timeRef

    # Converts seconds to HHMM. :02d formats it such that there is a leading zero if needed
    if ttcCompared > 0:
        timeRemainingH = int(ttcCompared // 3600)
        timeRemainingM = int((ttcCompared % 3600) // 60)

        if timeRemainingH > 0:
            ttcReturn = f'-{timeRemainingH}:{timeRemainingM:02d}' 
        else:
            ttcReturn = f'-{timeRemainingM:02d}'

    if ttcCompared < 0:
        timeRemainingH = int(-ttcCompared // 3600)
        timeRemainingM = int((-ttcCompared % 3600) // 60)

        if timeRemainingH > 0:
            ttcReturn = f'{timeRemainingH}:{timeRemainingM:02d}'
        else:
            ttcReturn = f'{timeRemainingM:02d}'

    if ttcCompared == 0:
        ttcReturn = '0'

    if verboseLog:
        print(f'{handlerID}Time comparison function variables:\nTime to Compare: {ttc}\nIs Game Time: {isGameTime}\nReference Time: {timeRef}\nCompared Time (seconds): {ttcCompared}\nTime Remaining (H): {timeRemainingH}\nTime Remaining (M): {timeRemainingM}\nReturned TTD: {ttcReturn}')

    return ttcReturn

def getSimbriefData():
    sbDataPresent = False
    sbTOBT = ''
    sbEoC = [0,0,0,0,0]
    sbTimeToEoC = ''
    sbCallsign = ''
    sbCallsignFull = ''
    sbRWY = ''
    sbSID = ''

    sb = getSimbrief()

    if sb:
        if sb.last_error:
            print(f'{handlerID}Simbrief Error: {sb.last_error}')
        else:
            sbCallsignFull = sb.callsign
            # Prevents 7 character long callsigns from causing issues
            if len(sbCallsignFull) > 6:
                sbCallsign = sbCallsignFull[-4:]
            else:
                sbCallsign = sbCallsignFull

            sbTOBT = sb.sched_out
            sbEoC = sb.sched_off
            sbTimeToEoC = compareTime(sb.sched_off, True)
            sbRWY = sb.plan_rwy
            sbSID = sb.sid_ident

            sbDataPresent = True

    if verboseLog:
        print(f'{handlerID}Simbrief function variable log:\nSimbrief Data Present: {sbDataPresent}\nCallsign: {sbCallsignFull} shortened to {sbCallsign}\n\nTOBT: {sbTOBT}\nEoC: {sbEoC}\nTime to EoC: {sbTimeToEoC}\nRunway: {sbRWY}\nSID: {sbSID}')

    return sbDataPresent, sbCallsign, sbTOBT, sbEoC, sbTimeToEoC, sbRWY, sbSID

def testVATSIM(cid):
    VATSIMApiReturn = fetchJson('https://data.vatsim.net/v3/vatsim-data.json', 10, True)
    vtDataPresent = False
    vtCallsignFull = ''
    vtCallsign = ''
    vtICAO = ''
    airportOnline = False

    # This never happens but in case VATSIM like disintegrates or something I guess it's a good fallback. I added it during testing with a local API
    if VATSIMApiReturn == None:
        print(f'{handlerID}VATSIM datafile returned no data.')

    else:
        for pilot in VATSIMApiReturn['pilots']:
            if pilot['cid'] == int(cid):
                vtCallsignFull = pilot['callsign']
                # Prevents 7 character long callsigns from causing issues
                if len(vtCallsignFull) > 6:
                    vtCallsign = vtCallsignFull[-4:]
                else:
                    vtCallsign = vtCallsignFull
                vtICAO = pilot['flight_plan']['aircraft_short']
                vtDataPresent = True

        # Check if ESSA is online. If not, don't ping CDM because if ESSA is offline then CDM is going to be empty
        for controller in VATSIMApiReturn["controllers"]:
            if controller['callsign'] in airportATC:
                airportOnline = True

        for atis in VATSIMApiReturn["atis"]:
            if atis['callsign'] in airportATC:
                airportOnline = True

    if verboseLog:
        print(f'{handlerID}VATSIM function variable log:\nVATSIM API Data Present: {vtDataPresent}\nESSA Online on VATSIM: {airportOnline}\nCallsign: {vtCallsignFull} shortened to {vtCallsign}\nAircraft ICAO: {vtICAO}')

    return vtDataPresent, vtCallsignFull, vtICAO, airportOnline, vtCallsign

def getCDM(callsign):
    CDMEoC = [0,0,0,0,0]
    CDMTimeToEoC = ''
    CDMTOBT = ''
    CDMTSAT = ''
    CDMisCtot = False
    CDMDepInfo = ''
    CDMRWY = ''
    CDMSID = ''
    CDMAPIOffline = False

    CDMAPIReturn = fetchJson(f'https://cdm-server-production.up.railway.app/ifps/callsign?callsign={callsign}', timeout=10, etag=True)

    # CDM API can, on rare occasions, be down, this is a fallback for that
    if CDMAPIReturn == None:
        print(f'{handlerID}CDM API returned no data.')
        CDMAPIOffline = True
    else:
        # It's possible that TOBT and TSAT fields will be empty if CDM isn't applied so this handles that edgecase as EOBT should always be defined
        if (CDMAPIReturn['cdmData'])['tobt'] == '':
            CDMTOBT = hhmmssToObj(CDMAPIReturn['eobt'])
        else:
            CDMTOBT = hhmmssToObj((CDMAPIReturn['cdmData'])['tobt'])

        if (CDMAPIReturn['cdmData'])['tsat'] == '':
            CDMTSAT = CDMTOBT
        else:
            CDMTSAT = hhmmssToObj((CDMAPIReturn['cdmData'])['tsat'])

        # TTOT can be given if CDM in use but defaults to using TSAT + taxi time if it's not present
        if (CDMAPIReturn['cdmData'])['ttot'] == '':
            CDMEoC = time.gmtime(calendar.timegm(CDMTSAT) + (CDMAPIReturn['taxi'] * 60))
            CDMisCtot = False
        else:
            CDMEoC = hhmmssToObj((CDMAPIReturn['cdmData'])['ttot'])
            CDMisCtot = True

        sb = getSimbrief()

        if (CDMAPIReturn['cdmData'])['depInfo'] != '':
            CDMDepInfo = ((CDMAPIReturn['cdmData'])['depInfo']).split('/')
            
            CDMRWY = CDMDepInfo[0]
            if len(CDMDepInfo[1]) > 6:
                CDMSID = f'{CDMDepInfo[1][0:4]}{CDMDepInfo[1][-2:]}'
            else:
                CDMSID = CDMDepInfo[1]
        
        else:
            if sb:
                if sb.last_error:
                    print(f'{handlerID}Simbrief Error: {sb.last_error}')
                else:
                    CDMRWY = sb.plan_rwy
                    CDMSID = sb.sid_ident

        CDMTimeToEoC = compareTime(CDMEoC, False)

    return CDMEoC, CDMTimeToEoC, CDMTOBT, CDMTSAT, CDMRWY, CDMSID, CDMisCtot, CDMAPIOffline

def CDMHandlerHub():
    global showChockandGate, showPaxCargoFuel
    sbPass = False

    varVATSIMCID = getGlobalPersistentVariable('vatsim_cid')
    if varVATSIMCID == None:
        if (userVarVATSIMCID == '<CID>') and (getGlobalPersistentVariable('vatsim_cid') == None):
            print('No VATSIM CID is set in the script. Please set one.')
            varVATSIMCID = 0
        else:
            setGlobalPersistentVariable('vatsim_cid', userVarVATSIMCID)
            varVATSIMCID = userVarVATSIMCID

    if verboseLog:
        print(f'{handlerID}VATSIM CID used for handler: {varVATSIMCID}. Global persistent variable return: {getGlobalPersistentVariable("vatsim_cid")}')

    # Only run the script if the VDGS system is the SafeDockT2S-24
    if "SafeDockTS24" not in (getGate().parkingSystem):
        print(f'{handlerID}VDGS System is not supported.')
    else:
        # Delay to give GSX time to get Simbrief data and for the VDGS unit to initialize
        truewait(12500)

        while True:
            # Checks to make sure Simbrief data is valid, if not, refreshes it in case the user forgets
            if not sbPass:
                sbData = reloadSimbrief()
                if sbData.last_error:
                    print(f'{handlerID}Simbrief error: {sbData.last_error}')
                else:
                    sbPass = True

            if verboseLog:
                print(f'{handlerID}Starting handler cycle')

            vTestVATSIM = testVATSIM(varVATSIMCID)
            vGetSB = getSimbriefData()

            if verboseLog:
                print(f'{handlerID}VATSIM Data Present: {vTestVATSIM[0]}, Airport online on VATSIM: {vTestVATSIM[3]}, Simbrief Data Present: {vGetSB[0]}')

            if (vTestVATSIM[0] == True) and (vTestVATSIM[3] == True):
                vGetCDM = getCDM(vTestVATSIM[1])
                if vGetCDM[7] == True:
                    if verboseLog:
                        print(f'{handlerID}CDM API is offline, using Simbrief data as fallback.')
                    setVDGS(vGetSB[2], vGetSB[2], False, vGetSB[3], vGetSB[4], vGetSB[6], vGetSB[5], 'SIMBRF')
                else:
                    setVDGS(vGetCDM[2], vGetCDM[3], vGetCDM[6], vGetCDM[0], vGetCDM[1], vGetCDM[5], vGetCDM[4], 'VATSIM')

            else:
                if vGetSB[0] == True:
                    setVDGS(vGetSB[2], vGetSB[2], False, vGetSB[3], vGetSB[4], vGetSB[6], vGetSB[5], 'SIMBRF')

            # Cycle duration depends on the choices the user has made in regards to what to show to ensure that the cycle never resets mid sequence and that data isn't called needlessly often
            if showChockandGate and showPaxCargoFuel:
                truewait(vdgsDuration * vdgsPages + 16000)
            elif showPaxCargoFuel:
                truewait(vdgsDuration * vdgsPages + 12000)
            elif showChockandGate:
                truewait(vdgsDuration * vdgsPages + 4000)
            else:
                truewait(vdgsDuration * vdgsPages)
                
def setVDGS(TOBT, TSAT, isCTOT, EoCVar, TimeToEoC, SID, RWY, dataType):
    global showChockandGate, showPaxCargoFuel

    TOBT = splitTime(TOBT)
    TSAT = splitTime(TSAT)
    EoCVar = splitTime(EoCVar)

    if isCTOT:
        EoC = 'CTOT'
    else:
        EoC = 'ETD'

    if verboseLog:
        print(f'{handlerID}Data received by setVDGS():\nTOBT: {TOBT}\nTSAT: {TSAT}\nETD or CTOT Type: {EoC}\nEoC Time: {EoCVar}\nTime to EoC: {TimeToEoC}\nSID: {SID}\nRWY: {RWY}\nData Type (VATSIM or SIMBRF): {dataType}')

    addVdgsMessage({
        "id": "flight_information",
        "display": {
            "narrow": {
                "pages": [
                    {"lines": [
                        "TOBT",
                        TOBT,
                        "TSAT",
                        TSAT,
                        "",
                        dataType
                    ], "duration": vdgsDuration},
                    {"lines": [
                        "",
                        EoC,
                        EoCVar,
                        TimeToEoC,
                        "",
                        dataType
                    ], "duration": vdgsDuration},
                    {"lines": [
                        "SID",
                        SID,
                        "RWY",
                        RWY,
                        "",
                        dataType
                    ], "duration": vdgsDuration}
                ]
            }
        }
    })

    # These two parts disable the Chock and Gate display and the Pax Cargo Fuel display if the respective variables are false. If they are true, these functions aren't called and thus nothing changes
    if not showChockandGate:
        addVdgsMessage({
            "id": "chock_and_gate_display",
            "display": {
                "narrow": {
                    "pages": [
                        {"lines": [
                            ''
                        ], "duration": 0}
                    ]
                }
            }
        })
    
    if not showPaxCargoFuel:
        addVdgsMessage({
            "id": "passenger_cargo_info",
            "display": {
                "narrow": {
                    "pages": [
                        {"lines": [
                            ''
                        ], "duration": 0}
                    ]
                }
            }
        })

# Locks the handler cycle to prevent multiple instances of the cycle running at the same time
def handlerCycleLock():
    global handlerCycleRunning
    if verboseLog:
        print(f'{handlerID}Handler cycle running: {handlerCycleRunning}')
    if not handlerCycleRunning:
        handlerCycleRunning = True
        CDMHandlerHub()

def onAircraftEngaged(self):
    runAsync(handlerCycleLock)

def onBoardingRequested(self):
    runAsync(handlerCycleLock)

def onRefuelingRequested(self):
    runAsync(handlerCycleLock)

# Handler script created by Linas / Likeusb. Contacts: @likeusb on Discord