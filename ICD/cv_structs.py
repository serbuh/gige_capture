import enum
from ICD import cu_mrg

class activateCameraSensors(enum.Enum):
    camera1     = 1,
    camera2     = 2,
    camera1And2 = 3,
    
    def to_ctypes_value(self):
        return getattr(cu_mrg.activateCameraSensors, self.name)


class vision_status_msg(cu_mrg.CvStatusMessage):
    def __str__(self):
        return f"Frame {self.cameraStatus.frameId} @ {self.cameraStatus.fps} [Hz] bitrate {self.cameraStatus.bitrateKBs} offset({self.cameraStatus.cameraOffsetX}, {self.cameraStatus.cameraOffsetY}) calibration {self.cameraStatus.calibration} addOverlay {self.cameraStatus.addOverlay}"

class client_set_params_msg(cu_mrg.SetCvParamsCmdMessage):
    def __str__(self):
        return f"Frame {self.cameraControl.frameId} @ {self.cameraControl.fps} [Hz] bitrate {self.cameraControl.bitrateKBs} offset({self.cameraControl.cameraOffsetX}, {self.cameraControl.cameraOffsetY}) calibration {'(V)' if self.cameraControl.calibration else '(X)'} addOverlay {'(V)' if self.cameraControl.addOverlay else '(X)'}"

class vision_set_params_ack_msg(cu_mrg.SetCvParamsAckMessage):
    def __str__(self):
        if self.result.isOk.value==self.result.isOk.TRUE_:
            res_str="Ok"
        else:
            res_str=f"errorCode({self.result.errorCode})"
        return f"ACK ({res_str})"

# Create status
def create_status(frameId, fps, bitrateKBs, calibration, addOverlay):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage)

    cameraStatus = cu_mrg.cameraControlStruct(frameId=frameId, cameraOffsetX=0, cameraOffsetY=0, fps=fps, bitrateKBs=bitrateKBs, calibration=calibration, addOverlay=addOverlay) # Cam status

    return vision_status_msg(header=header, cameraStatus=cameraStatus)

# Create params reply
def create_cv_command_ack(isOk, errorCode=0):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage)
    result = cu_mrg.setCvParamsResultStruct(isOk=isOk, errorCode=errorCode)
    return vision_set_params_ack_msg(header=header, result=result)

def create_cv_command(frameId, fps, bitrateKBs, calibration, addOverlay):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsCmdMessage)
    
    cameraControl = cu_mrg.cameraControlStruct(frameId=frameId, cameraOffsetX=0, cameraOffsetY=0, fps=fps, bitrateKBs=bitrateKBs, calibration=calibration, addOverlay=addOverlay) # Cam params
    
    # Build message
    return client_set_params_msg(header=header, cameraControl=cameraControl)
