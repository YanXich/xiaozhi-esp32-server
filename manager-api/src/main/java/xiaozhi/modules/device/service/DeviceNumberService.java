package xiaozhi.modules.device.service;

import xiaozhi.common.service.BaseService;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.device.entity.DeviceNumberEntity;

import java.util.List;

public interface DeviceNumberService extends BaseService<DeviceNumberEntity> {
    
    /**
     * Export device numbers by batch ID
     * @param batchId Batch ID
     * @return Device numbers separated by newlines
     */
    String exportDeviceNumbers(Long batchId);
    
    /**
     * Query device numbers by batch ID with pagination
     * @param batchId Batch ID
     * @param page Page number
     * @param limit Page size
     * @return Paginated device numbers
     */
    PageData<DeviceNumberEntity> queryDeviceNumbers(Long batchId, Integer page, Integer limit);
    
    /**
     * Query device numbers by batch ID and device number with pagination
     * @param batchId Batch ID
     * @param deviceNumber Device number filter
     * @param page Page number
     * @param limit Page size
     * @return Paginated device numbers
     */
    PageData<DeviceNumberEntity> queryDeviceNumbers(Long batchId, String deviceNumber, Integer page, Integer limit);
    
    /**
     * Query device numbers without batch with pagination
     * @param page Page number
     * @param limit Page size
     * @return Paginated device numbers
     */
    PageData<DeviceNumberEntity> queryDeviceNumbersWithoutBatch(Integer page, Integer limit, String name);
    
    /**
     * List device numbers by batch ID
     * @param batchId Batch ID
     * @return List of device numbers
     */
    List<DeviceNumberEntity> listDeviceNumbersByBatchId(Long batchId);
    
    /**
     * Save batch of device numbers
     * @param deviceNumberEntities List of device number entities
     */
    void saveBatch(List<DeviceNumberEntity> deviceNumberEntities);
    
    /**
     * Update device number status
     * @param id Device number ID
     * @param status New status
     * @return Update success flag
     */
    boolean updateDeviceNumberStatus(Long id, Integer status);
}