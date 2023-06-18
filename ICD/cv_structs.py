from ICD import cu_mrg

class vision_status_msg(cu_mrg.CvStatusMessage):
    def __str__(self):
        return f"{self.cvStatus.camera1Status.frameId}"

class client_set_params_msg(cu_mrg.SetCvParamsCmdMessage):
    def __str__(self):
        return f"{self.cvParams.camera1Control.frameId}"

class vision_set_params_ack_msg(cu_mrg.SetCvParamsAckMessage):
    def __str__(self):
        if self.result.isOk.value==self.result.isOk.TRUE_:
            res_str="Ok"
        else:
            res_str=f"Error({self.result.errorCode})"
        return f"ACK ({res_str})"

# Create status
def create_status(fps_1, fps_2, frame_number_1, frame_number_2):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage)

    # Cam 1 status
    cam1_status= cu_mrg.cameraControlStruct(frameId=frame_number_1, cameraOffsetX=2, cameraOffsetY=3, fps=fps_1, bitrateKBs=1000)
    
    # Cam 2 status
    cam2_status= cu_mrg.cameraControlStruct(frameId=frame_number_2, cameraOffsetX=4, cameraOffsetY=5, fps=fps_2, bitrateKBs=1500)

    # Active sensor
    active_sensor = cu_mrg.activateCameraSensors.camera1

    # Build status
    cvStatus = cu_mrg.cvStatusStruct(camera1Status=cam1_status, camera2Status=cam2_status, selectedCameraSensors=active_sensor)
    
    return cu_mrg.CvStatusMessage(header=header, cvStatus=cvStatus)

# Create params reply
def create_cv_command_ack(isOk, errorCode=0):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage)
    result = cu_mrg.setCvParamsResultStruct(isOk=isOk, errorCode=errorCode)
    return cu_mrg.SetCvParamsAckMessage(header=header, result=result)

def create_cv_command(fps_1, fps_2, bitrateKBs_1, bitrateKBs_2, active_sensor):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsCmdMessage)

    # Cam 1 params
    camera1Control = cu_mrg.cameraControlStruct(frameId=0, cameraOffsetX=0, cameraOffsetY=0, fps=fps_1, bitrateKBs=bitrateKBs_1)

    # Cam 2 params
    camera2Control = cu_mrg.cameraControlStruct(frameId=0, cameraOffsetX=0, cameraOffsetY=0, fps=fps_2, bitrateKBs=bitrateKBs_2)

    # Active sensor
    if active_sensor == 0:
        selectedCameraSensors = cu_mrg.activateCameraSensors.camera1And2
    elif active_sensor == 1:
        selectedCameraSensors = cu_mrg.activateCameraSensors.camera1
    elif active_sensor == 2:
        selectedCameraSensors = cu_mrg.activateCameraSensors.camera2
    
    # Build all params together
    cvParams = cu_mrg.setCvParamsCmdStruct(camera1Control=camera1Control, camera2Control=camera2Control, selectedCameraSensors=selectedCameraSensors)

    # Build message
    return cu_mrg.SetCvParamsCmdMessage(header=header, cvParams=cvParams)
