from ICD import cu_mrg

class vision_status_msg(cu_mrg.CvStatusMessage):
    def __str__(self):
        cam_info= lambda cam : f"Frame {cam.frameId} @ {cam.fps} [Hz] bitrate {cam.bitrateKBs} offset({cam.cameraOffsetX}, {cam.cameraOffsetY})"
        cam_1_str = cam_info(self.cvStatus.camera1Status)
        cam_2_str = cam_info(self.cvStatus.camera2Status)
        if self.cvStatus.selectedCameraSensors.value == cu_mrg.activateCameraSensors.camera1:
            active_cam = "1"
        elif self.cvStatus.selectedCameraSensors.value == cu_mrg.activateCameraSensors.camera2:
            active_cam = "2"
        elif self.cvStatus.selectedCameraSensors.value == cu_mrg.activateCameraSensors.camera1And2:
            active_cam = "1 and 2"
        return f"{cam_1_str}\n{cam_2_str}\nActive Cam: {active_cam}"

class client_set_params_msg(cu_mrg.SetCvParamsCmdMessage):
    def __str__(self):
        cam_info= lambda cam : f"Frame {cam.frameId} @ {cam.fps} [Hz] bitrate {cam.bitrateKBs} offset({cam.cameraOffsetX}, {cam.cameraOffsetY})"
        cam_1_str = cam_info(self.cvParams.camera1Control)
        cam_2_str = cam_info(self.cvParams.camera2Control)
        if self.cvParams.selectedCameraSensors.value == cu_mrg.activateCameraSensors.camera1:
            active_cam = "1"
        elif self.cvParams.selectedCameraSensors.value == cu_mrg.activateCameraSensors.camera2:
            active_cam = "2"
        elif self.cvParams.selectedCameraSensors.value == cu_mrg.activateCameraSensors.camera1And2:
            active_cam = "1 and 2"
        return f"{cam_1_str}\n{cam_2_str}\nActive Cam: {active_cam}"

class vision_set_params_ack_msg(cu_mrg.SetCvParamsAckMessage):
    def __str__(self):
        if self.result.isOk.value==self.result.isOk.TRUE_:
            res_str="Ok"
        else:
            res_str=f"errorCode({self.result.errorCode})"
        return f"ACK ({res_str})"

# Create status
def create_status(frame_number_1, frame_number_2, fps_1, fps_2, bitrateKBs_1, bitrateKBs_2):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage)

    cam1_status= cu_mrg.cameraControlStruct(frameId=frame_number_1, cameraOffsetX=2, cameraOffsetY=3, fps=fps_1, bitrateKBs=bitrateKBs_1) # Cam 1 status
    cam2_status= cu_mrg.cameraControlStruct(frameId=frame_number_2, cameraOffsetX=4, cameraOffsetY=5, fps=fps_2, bitrateKBs=bitrateKBs_2) # Cam 2 status
    active_sensor = cu_mrg.activateCameraSensors.camera1 # Active sensor
    
    cvStatus = cu_mrg.cvStatusStruct(camera1Status=cam1_status, camera2Status=cam2_status, selectedCameraSensors=active_sensor) # Build status
    
    return vision_status_msg(header=header, cvStatus=cvStatus)

# Create params reply
def create_cv_command_ack(isOk, errorCode=0):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage)
    result = cu_mrg.setCvParamsResultStruct(isOk=isOk, errorCode=errorCode)
    return vision_set_params_ack_msg(header=header, result=result)

def create_cv_command(fps_1, fps_2, bitrateKBs_1, bitrateKBs_2, active_sensor):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsCmdMessage)
    
    camera1Control = cu_mrg.cameraControlStruct(frameId=0, cameraOffsetX=0, cameraOffsetY=0, fps=fps_1, bitrateKBs=bitrateKBs_1) # Cam 1 params
    camera2Control = cu_mrg.cameraControlStruct(frameId=0, cameraOffsetX=0, cameraOffsetY=0, fps=fps_2, bitrateKBs=bitrateKBs_2) # Cam 2 params

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
    return client_set_params_msg(header=header, cvParams=cvParams)
