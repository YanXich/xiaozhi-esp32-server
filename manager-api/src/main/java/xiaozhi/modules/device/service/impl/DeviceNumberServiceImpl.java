package xiaozhi.modules.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.device.dao.DeviceNumberDao;
import xiaozhi.modules.device.entity.DeviceNumberEntity;
import xiaozhi.modules.device.dto.DeviceNumberGenerateDTO;
import xiaozhi.modules.device.service.DeviceNumberService;
import xiaozhi.common.page.PageData;
import com.baomidou.mybatisplus.core.metadata.IPage;
import java.util.HashMap;
import java.util.Map;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;
import xiaozhi.common.constant.Constant;

// 添加缺失的导入
import xiaozhi.modules.device.entity.DeviceProductionBatchEntity;
import xiaozhi.modules.device.entity.DeviceFactoryEntity;

@Slf4j
@Service
@AllArgsConstructor
public class DeviceNumberServiceImpl extends BaseServiceImpl<DeviceNumberDao, DeviceNumberEntity> implements DeviceNumberService {

    private final DeviceNumberDao deviceNumberDao;

    @Override
    public String exportDeviceNumbers(Long batchId) {
        QueryWrapper<DeviceNumberEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("batch_id", batchId);
        List<DeviceNumberEntity> deviceNumbers = deviceNumberDao.selectList(queryWrapper);
        
        return deviceNumbers.stream()
                .map(DeviceNumberEntity::getDeviceNumber)
                .collect(Collectors.joining("\n"));
    }
    
    @Override
    public PageData<DeviceNumberEntity> queryDeviceNumbers(Long batchId, Integer page, Integer limit) {
        Map<String, Object> params = new HashMap<>();
        params.put(Constant.PAGE, String.valueOf(page));
        params.put(Constant.LIMIT, String.valueOf(limit));
        IPage<DeviceNumberEntity> iPage = getPage(params, "id", false);
        
        QueryWrapper<DeviceNumberEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("batch_id", batchId);
        //queryWrapper.orderByAsc("create_date");
        queryWrapper.orderByDesc("id");
        
        IPage<DeviceNumberEntity> resultPage = deviceNumberDao.selectPage(iPage, queryWrapper);
        return new PageData<>(resultPage.getRecords(), resultPage.getTotal());
    }
    
    @Override
    public PageData<DeviceNumberEntity> queryDeviceNumbers(Long batchId, String deviceNumber, Integer page, Integer limit) {
        Map<String, Object> params = new HashMap<>();
        params.put(Constant.PAGE, String.valueOf(page));
        params.put(Constant.LIMIT, String.valueOf(limit));
        IPage<DeviceNumberEntity> iPage = getPage(params, "id", false);
        
        QueryWrapper<DeviceNumberEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("batch_id", batchId);
        if (deviceNumber != null && !deviceNumber.isEmpty()) {
            queryWrapper.like("device_number", deviceNumber);
        }
        queryWrapper.orderByDesc("id");
        
        IPage<DeviceNumberEntity> resultPage = deviceNumberDao.selectPage(iPage, queryWrapper);
        return new PageData<>(resultPage.getRecords(), resultPage.getTotal());
    }
    
    @Override
    public PageData<DeviceNumberEntity> queryDeviceNumbersWithoutBatch(Integer page, Integer limit, String name) {
        Map<String, Object> params = new HashMap<>();
        params.put(Constant.PAGE, String.valueOf(page));
        params.put(Constant.LIMIT, String.valueOf(limit));
        IPage<DeviceNumberEntity> iPage = getPage(params, "id", false);
        
        QueryWrapper<DeviceNumberEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByAsc("create_date");
        
        // 检查params中是否有name参数，如果不为空字符串，则模糊搜索device_number字段
        if (name != null && !name.trim().isEmpty()) {
            queryWrapper.like("device_number", name.trim());
        }

        IPage<DeviceNumberEntity> resultPage = deviceNumberDao.selectPage(iPage, queryWrapper);
        return new PageData<>(resultPage.getRecords(), resultPage.getTotal());
    }
    
    @Override
    public List<DeviceNumberEntity> listDeviceNumbersByBatchId(Long batchId) {
        QueryWrapper<DeviceNumberEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("batch_id", batchId);
        queryWrapper.orderByAsc("create_date");
        return deviceNumberDao.selectList(queryWrapper);
    }
    
    @Override
    public void saveBatch(List<DeviceNumberEntity> deviceNumberEntities) {
        // 使用 deviceNumberDao 执行批量插入而不是调用 super.saveBatch
        if (deviceNumberEntities != null && !deviceNumberEntities.isEmpty()) {
            // 如果批量插入方法不可用，则逐个插入
            for (DeviceNumberEntity entity : deviceNumberEntities) {
                deviceNumberDao.insert(entity);
            }
        }
    }

    @Override
    public boolean updateDeviceNumberStatus(Long id, Integer status) {
        DeviceNumberEntity entity = deviceNumberDao.selectById(id);
        if (entity != null) {
            entity.setStatus(status);
            return deviceNumberDao.updateById(entity) > 0;
        }
        return false;
    }
}