package xiaozhi.modules.device.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import xiaozhi.modules.device.entity.DeviceProductionBatchEntity;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface DeviceProductionBatchDao extends BaseMapper<DeviceProductionBatchEntity> {
    
    @Select("SELECT COALESCE(MAX(end_serial_number), 0) FROM device_production_batch WHERE factory_id = #{factoryId}")
    Integer getMaxSerialNumber(@Param("factoryId") Long factoryId);
}