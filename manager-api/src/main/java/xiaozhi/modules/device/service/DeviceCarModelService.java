package xiaozhi.modules.device.service;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.entity.DeviceCarModelEntity;
import xiaozhi.modules.device.dto.DeviceCarModelDTO;
import xiaozhi.common.page.PageData;
import java.util.List;
import java.util.Map;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

public interface DeviceCarModelService extends BaseService<DeviceCarModelEntity> {
    PageData<DeviceCarModelEntity> queryCarModels(Map<String, Object> params);
    List<DeviceCarModelEntity> listCarModels(DeviceCarModelDTO queryDTO);
    
    // 添加删除方法
    void delete(Long id);
    
    // 添加selectOne方法
    DeviceCarModelEntity selectOne(QueryWrapper<DeviceCarModelEntity> queryWrapper);
}