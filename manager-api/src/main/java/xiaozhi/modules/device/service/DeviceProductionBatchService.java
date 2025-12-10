package xiaozhi.modules.device.service;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.dto.DeviceProductionBatchDTO;
import xiaozhi.modules.device.entity.DeviceProductionBatchEntity;

import java.util.List;

public interface DeviceProductionBatchService extends BaseService<DeviceProductionBatchEntity> {
    
    PageData<DeviceProductionBatchEntity> queryBatches(DeviceProductionBatchDTO queryDTO);
    
    List<DeviceProductionBatchEntity> listBatches(DeviceProductionBatchDTO queryDTO);
    
    Integer getMaxSerialNumber(Long factoryId);
}