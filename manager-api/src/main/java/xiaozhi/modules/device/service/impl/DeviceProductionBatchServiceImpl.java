package xiaozhi.modules.device.service.impl;

import lombok.AllArgsConstructor;
import org.springframework.stereotype.Service;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.device.dao.DeviceProductionBatchDao;
import xiaozhi.modules.device.entity.DeviceProductionBatchEntity;
import xiaozhi.modules.device.service.DeviceProductionBatchService;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.device.dto.DeviceProductionBatchDTO;
import java.util.List;
import java.util.HashMap;
import java.util.Map;
import xiaozhi.common.constant.Constant;

@Service
@AllArgsConstructor
public class DeviceProductionBatchServiceImpl extends BaseServiceImpl<DeviceProductionBatchDao, DeviceProductionBatchEntity> implements DeviceProductionBatchService {
    
    private final DeviceProductionBatchDao deviceProductionBatchDao;
    
    @Override
    public PageData<DeviceProductionBatchEntity> queryBatches(DeviceProductionBatchDTO queryDTO) {
        // 修复分页参数传递问题，确保类型正确
        Map<String, Object> params = new HashMap<>();
        params.put(Constant.PAGE, String.valueOf(queryDTO.getPage()));
        params.put(Constant.LIMIT, String.valueOf(queryDTO.getLimit()));
        IPage<DeviceProductionBatchEntity> page = getPage(params, "create_date", false);
        
        QueryWrapper<DeviceProductionBatchEntity> queryWrapper = buildQueryWrapper(queryDTO);
        
        IPage<DeviceProductionBatchEntity> resultPage = deviceProductionBatchDao.selectPage(page, queryWrapper);
        return new PageData<>(resultPage.getRecords(), resultPage.getTotal());
    }
    
    @Override
    public List<DeviceProductionBatchEntity> listBatches(DeviceProductionBatchDTO queryDTO) {
        QueryWrapper<DeviceProductionBatchEntity> queryWrapper = buildQueryWrapper(queryDTO);
        return deviceProductionBatchDao.selectList(queryWrapper);
    }
    
    @Override
    public Integer getMaxSerialNumber(Long factoryId) {
        return deviceProductionBatchDao.getMaxSerialNumber(factoryId);
    }
    
    private QueryWrapper<DeviceProductionBatchEntity> buildQueryWrapper(DeviceProductionBatchDTO queryDTO) {
        QueryWrapper<DeviceProductionBatchEntity> queryWrapper = new QueryWrapper<>();
        
        // 工厂ID查询
        if (queryDTO.getFactoryId() != null) {
            queryWrapper.eq("factory_id", queryDTO.getFactoryId());
        }
        
        // 型号查询
        if (queryDTO.getModelType() != null && !queryDTO.getModelType().trim().isEmpty()) {
            queryWrapper.eq("model_type", queryDTO.getModelType().trim());
        }
        
        // 状态查询 (现在使用数字而不是枚举)
        if (queryDTO.getStatus() != null && !queryDTO.getStatus().trim().isEmpty()) {
            queryWrapper.eq("status", Integer.parseInt(queryDTO.getStatus()));
        }
        
        // 硬件版本查询
        if (queryDTO.getHardwareVersion() != null && !queryDTO.getHardwareVersion().trim().isEmpty()) {
            queryWrapper.eq("hardware_version", Integer.parseInt(queryDTO.getHardwareVersion()));
        }

        // 开始日期范围查询 - 修复日期比较逻辑
        if (queryDTO.getProductionDate() != null && !queryDTO.getProductionDate().trim().isEmpty()) {
            // 将字符串日期解析为当天的开始时间 (00:00:00)
            String startDateStr = queryDTO.getProductionDate().trim();
            queryWrapper.ge("production_date", startDateStr + " 00:00:00");
        }
        
        // if (queryDTO.getEndDate() != null && !queryDTO.getEndDate().trim().isEmpty()) {
        //     queryWrapper.le("production_date", queryDTO.getEndDate());
        // }
        
        // 修改排序字段为create_date
        queryWrapper.orderByDesc("create_date");
        return queryWrapper;
    }
}