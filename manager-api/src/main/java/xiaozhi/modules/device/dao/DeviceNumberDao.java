package xiaozhi.modules.device.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import xiaozhi.modules.device.entity.DeviceNumberEntity;

import java.util.List;

@Mapper
public interface DeviceNumberDao extends BaseMapper<DeviceNumberEntity> {
    // 添加批量插入方法定义
    int insertBatchSomeColumn(@Param("list") List<DeviceNumberEntity> entityList);
    
    // 添加更新设备号状态的方法
    int updateDeviceNumberStatus(@Param("id") Long id, @Param("status") Integer status);
}