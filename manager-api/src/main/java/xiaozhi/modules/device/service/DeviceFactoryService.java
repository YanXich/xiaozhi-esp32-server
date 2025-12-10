package xiaozhi.modules.device.service;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.entity.DeviceFactoryEntity;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.device.dto.DeviceFactoryQueryDTO;

import java.util.List;

public interface DeviceFactoryService extends BaseService<DeviceFactoryEntity> {
    PageData<DeviceFactoryEntity> queryFactories(DeviceFactoryQueryDTO queryDTO);
    List<DeviceFactoryEntity> listFactories(DeviceFactoryQueryDTO queryDTO);
}