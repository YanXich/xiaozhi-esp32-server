package xiaozhi.modules.device.service;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.entity.DeviceMacEntity;
import xiaozhi.common.page.PageData;
import java.util.Map;

public interface DeviceMacService extends BaseService<DeviceMacEntity> {
    
    /**
     * Query device MAC configurations with pagination
     * @param params Query parameters
     * @return Paginated device MAC data
     */
    PageData<DeviceMacEntity> queryDeviceMacs(Map<String, Object> params);
    
    /**
     * Get device configuration by MAC address
     * @param macAddress MAC address
     * @return Device configuration data
     */
    String getDeviceConfigByMac(String macAddress);
}