from ICD import cu_mrg

# Create reply
def create_reply(isOk, errorCode=0):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage)
    result = cu_mrg.setCvParamsResultStruct(isOk=True, errorCode=errorCode)
    params_ack_msg = cu_mrg.SetCvParamsAckMessage(header=header, result=result)
    return params_ack_msg

def create_status():
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage)

    # Cam 1 status
    cam1_status= cu_mrg.cameraControlStruct(frameId=123, cameraOffsetX=2, cameraOffsetY=3, fps=20, bitrateKBs=1000)
    
    # Cam 2 status
    cam2_status= cu_mrg.cameraControlStruct(frameId=456, cameraOffsetX=4, cameraOffsetY=5, fps=25, bitrateKBs=1500)

    # Active sensor
    active_sensor = cu_mrg.activateCameraSensors.camera1

    cvStatus = cu_mrg.cvStatusStruct(camera1Status=cam1_status, camera2Status=cam2_status, selectedCameraSensors=active_sensor)
    status_msg = cu_mrg.CvStatusMessage(header=header, status=cvStatus)
    return status_msg

params_result_msg = create_reply(isOk=True)
status_msg = create_status()

# TODO get 
# class SetCvParamsCmdMessage(Structure):                     # (Opcode 0x32) Message 3250
#     _fields_ = [("header", headerStruct),
#                 ("cvParams", setCvParamsCmdStruct)]
