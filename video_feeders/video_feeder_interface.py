import abc

class VideoFeeder(abc.ABC):
    def __init__(self, artificial):
        self.artificial = artificial

    def is_artificial(self):
        return self.artificial

    @abc.abstractmethod
    def get_next_frame(self):
        """ Implement me! """
        pass

    @abc.abstractmethod
    def release_cam_buffer(self, cam_buffer):
        """ Implement me! """
        pass