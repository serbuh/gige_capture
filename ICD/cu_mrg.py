"""
	cu_mrg.py
	This file was created automatically by the RIDA IO application
	On: 11/07/2023 09:29:01
	Rida IO HFileWriter Version: 1.0, last update: 09/03/2023 18:53:36
	Rida Database Version: 1.0
	Header File Version marked as: 0.0
	ICD version marked as: 1003
	Produced by: SVC_MRG, On: MRG-DEV101
	Enhancements & Maintenance is done by Software Infrastructure team, 
	Missile Division.
	ALL RIGHTS RESERVED RAFAEL (C) 08-2014 
"""
import sys
from ctypes import *

"""
System Versions
"""
h_ver_cu_mrg = 0.0                                          # Header File Version
icd_ver_cu_mrg = 1003                                       # ICD Version
ridaDB_ver = 1.0                                            # Rida Database Version


"""
Constants
"""
ROUTE_MAX_SIZE = 200                                        # Constant 153
OBST_MAX_SIZE = 7000                                        # Constant 323
ZONE_SIZE = 4                                               # Constant 910


"""
Elements
"""
bool_ = c_ubyte                                             # Element 342
char_ = c_char                                              # Element 741
double_ = c_double                                          # Element 1485
float_ = c_float                                            # Element 2196
int_ = c_int                                                # Element 2756
unsigned_char = c_ubyte                                     # Element 3636
unsigned_int = c_uint                                       # Element 4230
unsigned_long_long = c_ulonglong                            # Element 4369
unsigned_short = c_ushort                                   # Element 5082
short_ = c_short                                            # Element 6232
geo10MicroDegInt16DiffType = c_short                        # Element 8424
geoCmInt16DiffType = c_short                                # Element 8544
routeIdType = c_ubyte                                       # Element 9008 - Describes current routeId. (Counter which overlaps when reaching max)
vehicleIdType = c_ubyte                                     # Element 9294
"""
	Element 10053 - +40 = Leftmost
	-40 = Rightmost
"""
wheelRotationType = c_float

linearSpeedType = c_float                                   # Element 10705
"""
	Element 14184 - NAV_NO_MEASUREMENT = 0,
	NAV_POS_MEASUREMENT = 1,
	NAV_VEL_MEASUREMENT = 2,
	NAV_POS_VEL_MEASUREMENT = 3,
	NAV_ODO_MEASUREMENT = 4,
	NAV_POS_VEL_ODO_MEASUREMENT = 5,
	NAV_ZLM_MEASUREMENT = 6,
	NAV_POS_ZLM_MEASUREMENT = 7,
	NAV_VEL_ZLM_MEASUREMENT = 8,
	NAV_POS_VEL_ZLM_MEASUREMENT = 9,
	NAV_POS_VEL_ODO_ZLM_MEASUREMENT = 10, 
	NAV_ZUPT_MEASUREMENT = 11,
	NAV_POS_ZUPT_MEASUREMENT = 12,
	NAV_VEL_ZUPT_MEASUREMENT = 13,
	NAV_POS_VEL_ZUPT_MEASUREMENT = 14,
	NAV_ODO_ZUPT_MEASUREMENT = 15,  Can be ZUP & ODO at the same time? 
	NAV_ZARU_MEASUREMENT = 16,
	NAV_POS_ZARU_MEASUREMENT = 17,
	NAV_VEL_ZARU_MEASUREMENT = 18,
	NAV_POS_VEL_ZARU_MEASUREMENT = 19,
	NAV_ODO_ZARU_MEASUREMENT = 20, 
	NAV_ZUPT_ZARU_MEASUREMENT = 21, 
	NAV_VEL_ZUPT_ZARU_MEASUREMENT = 22,
	NAV_POS_VEL_ZUPT_ZARU_MEASUREMENT = 23,
	NAV_BARO_MEASUREMENT = 24, 
	NAV_POS_BARO_MEASUREMENT = 25, 
	NAV_VEL_BARO_MEASUREMENT = 26, 
	NAV_POS_VEL_BARO_MEASUREMENT = 27,
	NAV_POS_BARO_ZUPT_MEASUREMENT = 28,
	NAV_POS_BARO_ZARU_MEASUREMENT = 29,
	NAV_POS_BARO_ZUPT_ZARU_MEASUREMENT = 30, 
	NAV_VEL_BARO_ZUPT_MEASUREMENT = 31, 
	NAV_POS_VEL_BARO_ZUPT_MEASUREMENT = 32,
	NAV_VEL_BARO_ZARU_MEASUREMENT = 33,
	NAV_POS_VEL_BARO_ZARU_MEASUREMENT = 34,
	NAV_VEL_BARO_ZUPT_ZARU_MEASUREMENT = 35, 
	NAV_POS_VEL_BARO_ZUPT_ZARU_MEASUREMENT = 36,
	NAV_BARO_ZUPT_MEASUREMENT = 37,
	NAV_BARO_ZARU_MEASUREMENT = 38,
	NAV_BARO_ZUPT_ZARU_MEASUREMENT = 39
"""
navMeasurementOptions = c_ubyte



"""
Enums
"""
class cuCmdOptions(c_ubyte):                                # Element 5280
    stop = 0
    manual = 1
    modeling = 2
    byRoute = 10
    inDoor = 20

class ezStatusOptions(c_ubyte):                             # Element 6727
    init = 0
    manual = 1
    modeling = 2
    stop = 3
    byRouteInProgress = 10
    byRouteCompleted = 11
    byRouteFailure = 12
    inDoorInProgressPath = 20
    inDoorInProgressTurnSearch = 21
    inDoorInProgressTurnning = 23
    inDoorInProgressTurnFinished = 24
    inDoorInProgressObjectPath = 25
    inDoorCompleted = 26
    inDoorFailure = 27
    fail = 255

class ezNavStatusOptions(c_ubyte):                          # Element 7331
    span_PPP = 0
    span_noNav = 1
    alg_fix = 2
    alg_noNav = 3

class trueOrFalseOptions(c_ubyte):                          # Element 8019
    FALSE_ = 0
    TRUE_ = 1

class leftRightOptions(c_ubyte):                            # Element 11625
    left = 0
    right = 1

class brakesOptions(c_ubyte):                               # Element 12557
    noneBrakes = 0
    frontBrakesOnly = 1
    rearBrakesOnly = 2
    allBrakes = 3

class navModeOptions(c_ubyte):                              # Element 12921
    navIdle = 0
    navInit = 1
    navInitFromLauncher = 2
    navInitFromGps = 3
    navAlign = 4
    navGroundAlign = 5
    navInsAlign = 6
    navGroundAlignFromGps = 7
    navNavigate = 8
    navFreeFlight = 9
    navInFlightAlign = 10

class navOverallStatusOptions(c_ubyte):                     # Element 13513
    navStatusIdle = 0
    navFatal = 1
    navBad = 2
    navNotAligned = 3
    navDegraded = 4
    navGood = 5

class activateCameraSensors(c_ubyte):                       # Element 14849
    camera1 = 1
    camera2 = 2
    camera1And2 = 3



"""
Opcodes
"""
class cu_mrg_Opcodes(c_uint16):
    OPcuCmdMessage = 0x4                                    # Opcode for Message 47 (Message name: cuCmdMessage)
    OPcuRouteCmdMessage = 0x5                               # Opcode for Message 404 (Message name: cuRouteCmdMessage)
    OPezObstStatusMessage = 0xF                             # Opcode for Message 1283 (Message name: ezObstStatusMessage)
    OPezStatusMessage = 0xE                                 # Opcode for Message 1879 (Message name: ezStatusMessage)
    OPStopCmdMessage = 0x9                                  # Opcode for Message 2396 (Message name: StopCmdMessage)
    OPSetCvParamsCmdMessage = 0x32                          # Opcode for Message 3250 (Message name: SetCvParamsCmdMessage)
    OPSetCvParamsAckMessage = 0x33                          # Opcode for Message 3826 (Message name: SetCvParamsAckMessage)
    OPCvStatusMessage = 0x30                                # Opcode for Message 4076 (Message name: CvStatusMessage)


"""
Structures
"""
class headerStruct(Structure):                              # Struct 2697
    _fields_ = [("opCode", unsigned_char),
                ("spare1", unsigned_char),
                ("msgCounter", unsigned_short),
                ("spare2", unsigned_char),
                ("spare3", unsigned_char),
                ("spare4", unsigned_char),
                ("spare5", unsigned_char),
                ("timeTagSeconds", double_)]

class coordinateGeoDiffInt16Struct(Structure):              # Struct 2833
    _fields_ = [("latDiff10MicroDeg", geo10MicroDegInt16DiffType),
                ("lonDiff10MicroDeg", geo10MicroDegInt16DiffType)]

class coordinateUtmDiffInt16Struct(Structure):              # Struct 3484
    _fields_ = [("eastDiffCm", geoCmInt16DiffType),
                ("northDiffCm", geoCmInt16DiffType)]

class coordinate2dGeoDegStruct(Structure):                  # Struct 4353
    _fields_ = [("latitudeGeoDeg", double_),
                ("longitudeGeoDeg", double_)]

class coordinate3dGeoDegStruct(Structure):                  # Struct 4770
    _fields_ = [("latitudeGeoDeg", double_),
                ("longitudeGeoDeg", double_),
                ("altGeoMeter", double_)]

class initLocationParamsStruct(Structure):                  # Struct 5648
    _fields_ = [("coordinates3d", coordinate3dGeoDegStruct),
                ("yawOrig_Deg", double_),
                ("pitchOrig_Deg", double_),
                ("rollOrig_Deg", double_)]

class coordinate2dUtmStruct(Structure):                     # Struct 6092
    _fields_ = [("eastMeters", double_),
                ("northMeters", double_),
                ("zone", unsigned_char*ZONE_SIZE)]

class cameraControlStruct(Structure):                       # Struct 7561
    _fields_ = [("frameId", unsigned_int),
                ("cameraOffsetX", unsigned_short),
                ("cameraOffsetY", unsigned_short),
                ("fps", unsigned_char),
                ("bitrateKBs", unsigned_char),
                ("calibration", trueOrFalseOptions),
                ("addOverlay", trueOrFalseOptions),
                ("spare0", unsigned_char),
                ("spare1", unsigned_char),
                ("spare2", unsigned_char),
                ("spare3", unsigned_char)]

class setCvParamsResultStruct(Structure):                   # Struct 7676
    _fields_ = [("isOk", trueOrFalseOptions),
                ("spare1", unsigned_char),
                ("errorCode", unsigned_short),
                ("spare4Bytes", unsigned_int)]


class cuCmdStruct(Structure):                               # Struct 627
    _fields_ = [("initParams", initLocationParamsStruct),
                ("linearSpeedKphCmd", linearSpeedType),
                ("wheelRotationDegCmd", wheelRotationType),
                ("icdVer", unsigned_short),
                ("inDoorRangeToTurnMeters", unsigned_char),
                ("inDoorTurnDirectionCmd", leftRightOptions),
                ("cuCmd", cuCmdOptions),
                ("resetCnt", unsigned_char),
                ("shouldRecord", trueOrFalseOptions),
                ("inDoorSpeedKmh", unsigned_char)]

class cuRouteCmdStruct(Structure):                          # Struct 1473
    _fields_ = [("orig2dCoordinate", coordinate2dGeoDegStruct),
                ("finalAz_deg", double_),
                ("maxSpeedKph", linearSpeedType),
                ("routeSize", unsigned_short),
                ("routeId", routeIdType),
                ("isFinalAzValid", trueOrFalseOptions),
                ("routeDiff", coordinateGeoDiffInt16Struct*ROUTE_MAX_SIZE)]

class ezObstStatusStruct(Structure):                        # Struct 1950
    _fields_ = [("orig2dUtmCoordinate", coordinate2dUtmStruct),
                ("spare4Bytes", unsigned_int),
                ("numOfObst", unsigned_short),
                ("spare2Bytes", unsigned_short),
                ("obstDiff", coordinateUtmDiffInt16Struct*OBST_MAX_SIZE)]

class ezStatusStruct(Structure):                            # Struct 2680
    _fields_ = [("ezCoordinates3d", coordinate3dGeoDegStruct),
                ("ezYaw_Deg", double_),
                ("ezPitch_Deg", double_),
                ("ezRoll_Deg", double_),
                ("totalDistanceCm", int_),
                ("linearSpeedKphStatus", linearSpeedType),
                ("wheelRotationDegStatus", wheelRotationType),
                ("icdVer", unsigned_short),
                ("ezNavStatus", ezNavStatusOptions),
                ("isLidarGood", trueOrFalseOptions),
                ("isImuGood", trueOrFalseOptions),
                ("isOdometerGood", trueOrFalseOptions),
                ("isVehicleGood", trueOrFalseOptions),
                ("isRecordsOn", trueOrFalseOptions),
                ("ezStatus", ezStatusOptions),
                ("brakesStatus", brakesOptions),
                ("isEmergencyBrakesActivated", trueOrFalseOptions),
                ("routeId", routeIdType),
                ("vehicleId", vehicleIdType),
                ("navMeasTypeMode", navMeasurementOptions),
                ("navMode", navModeOptions),
                ("navOverallNavigationStatus", navOverallStatusOptions),
                ("navMotionDetected", trueOrFalseOptions),
                ("spare1", unsigned_char),
                ("spare2", unsigned_char),
                ("spare3", unsigned_char)]



"""
Messages
"""
class cuCmdMessage(Structure):                              # (Opcode 0x4) Message 47
    _fields_ = [("header", headerStruct),
                ("cuCmd", cuCmdStruct)]

class cuRouteCmdMessage(Structure):                         # (Opcode 0x5) Message 404 - Sent on a new route requested by the user.
    _fields_ = [("header", headerStruct),
                ("cuRouteCmd", cuRouteCmdStruct)]

class ezObstStatusMessage(Structure):                       # (Opcode 0xF) Message 1283
    _fields_ = [("header", headerStruct),
                ("ezObstStatus", ezObstStatusStruct)]

class ezStatusMessage(Structure):                           # (Opcode 0xE) Message 1879
    _fields_ = [("header", headerStruct),
                ("ezStatus", ezStatusStruct)]

class StopCmdMessage(Structure):                            # (Opcode 0x9) Message 2396 - sent directly when user press "Stop" button.
    _fields_ = [("header", headerStruct)]

class SetCvParamsCmdMessage(Structure):                     # (Opcode 0x32) Message 3250
    _fields_ = [("header", headerStruct),
                ("cameraControl", cameraControlStruct)]

class SetCvParamsAckMessage(Structure):                     # (Opcode 0x33) Message 3826
    _fields_ = [("header", headerStruct),
                ("result", setCvParamsResultStruct)]

class CvStatusMessage(Structure):                           # (Opcode 0x30) Message 4076
    _fields_ = [("header", headerStruct),
                ("cameraStatus", cameraControlStruct)]


"""
	End of generated code.
"""
