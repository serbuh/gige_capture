from ICD import cu_mrg

# Create status
def create_status(frame_number_1, frame_number_2):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage)

    # Cam 1 status
    cam1_status= cu_mrg.cameraControlStruct(frameId=frame_number_1, cameraOffsetX=2, cameraOffsetY=3, fps=20, bitrateKBs=1000)
    
    # Cam 2 status
    cam2_status= cu_mrg.cameraControlStruct(frameId=frame_number_2, cameraOffsetX=4, cameraOffsetY=5, fps=25, bitrateKBs=1500)

    # Active sensor
    active_sensor = cu_mrg.activateCameraSensors.camera1

    cvStatus = cu_mrg.cvStatusStruct(camera1Status=cam1_status, camera2Status=cam2_status, selectedCameraSensors=active_sensor)
    status_msg = cu_mrg.CvStatusMessage(header=header, cvStatus=cvStatus)
    return status_msg

# Create params reply
def create_reply(isOk, errorCode=0):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage)
    result = cu_mrg.setCvParamsResultStruct(isOk=isOk, errorCode=errorCode)
    params_ack_msg = cu_mrg.SetCvParamsAckMessage(header=header, result=result)
    return params_ack_msg