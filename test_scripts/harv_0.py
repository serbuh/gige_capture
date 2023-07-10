from harvesters.core import Harvester
h = Harvester()
import cv2

expected_model = "mvBlueCOUGAR-X102eC"
#expected_model = "PT1000-CL4"

h.add_file('/opt/mvIMPACT_Acquire/lib/x86_64/mvGenTLProducer.cti')
h.update()

dev_id = None
for i,device in enumerate(h.device_info_list):
    print(i, device)
    if device.model == expected_model:
        print(f"Found {i}")
        dev_id = i
        break

print(f"Loading {dev_id}")

if dev_id is None:
    print(f"Model not found ({expected_model})")
    exit()

ia = h.create(dev_id)

#ia.remote_device.node_map.Width.value = 640
#ia.remote_device.node_map.Height.value = 640

ia.start()
while True:
    with ia.fetch() as buffer:
        component = buffer.payload.components[0]
        _1d = component.data
        _2d = component.data.reshape(component.height, component.width)

        cv2.imshow('stream0', _2d)
        key = cv2.waitKey(1)
        if key & 0xFF == 27:
            break

cv2.destroyAllWindows()
ia.stop()
ia.destroy()
h.reset()