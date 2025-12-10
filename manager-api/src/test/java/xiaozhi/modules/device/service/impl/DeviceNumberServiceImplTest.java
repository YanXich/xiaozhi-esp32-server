package xiaozhi.modules.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import xiaozhi.modules.device.dao.DeviceNumberDao;
import xiaozhi.modules.device.entity.DeviceNumberEntity;
import xiaozhi.modules.device.dto.DeviceNumberGenerateDTO;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DeviceNumberServiceImplTest {

    @Mock
    private DeviceNumberDao deviceNumberDao;

    @InjectMocks
    private DeviceNumberServiceImpl deviceNumberService;

    @Test
    void generateDeviceNumbers_WithValidDTO_ReturnsDeviceNumbers() {
        // Given
        DeviceNumberGenerateDTO dto = new DeviceNumberGenerateDTO();
        dto.setBatchId("batch1");
        dto.setCount(3);

        when(deviceNumberDao.insert(any(DeviceNumberEntity.class))).thenReturn(1);

        // When
        List<String> result = deviceNumberService.generateDeviceNumbers(dto);

        // Then
        assertNotNull(result);
        assertEquals(3, result.size());
        verify(deviceNumberDao, times(3)).insert(any(DeviceNumberEntity.class));
    }

    @Test
    void exportDeviceNumbers_WithValidBatchId_ReturnsExportString() {
        // Given
        String batchId = "batch1";
        DeviceNumberEntity number1 = new DeviceNumberEntity();
        number1.setDeviceNumber("1234567890");
        DeviceNumberEntity number2 = new DeviceNumberEntity();
        number2.setDeviceNumber("0987654321");

        when(deviceNumberDao.selectList(any(QueryWrapper.class))).thenReturn(Arrays.asList(number1, number2));

        // When
        String result = deviceNumberService.exportDeviceNumbers(batchId);

        // Then
        assertNotNull(result);
        assertTrue(result.contains("1234567890"));
        assertTrue(result.contains("0987654321"));
        verify(deviceNumberDao, times(1)).selectList(any(QueryWrapper.class));
    }

    @Test
    void queryDeviceNumbers_WithValidParams_ReturnsPageData() {
        // Given
        String batchId = "batch1";
        Integer page = 1;
        Integer limit = 10;

        DeviceNumberEntity number1 = new DeviceNumberEntity();
        number1.setId("number1");
        number1.setBatchId(batchId);
        number1.setDeviceNumber("1234567890");

        IPage<DeviceNumberEntity> iPage = new Page<>();
        iPage.setRecords(Arrays.asList(number1));
        iPage.setTotal(1L);

        when(deviceNumberDao.selectPage(any(), any(QueryWrapper.class))).thenReturn(iPage);

        // When
        var result = deviceNumberService.queryDeviceNumbers(batchId, page, limit);

        // Then
        assertNotNull(result);
        assertEquals(1, result.getTotal());
        assertEquals(1, result.getList().size());
        verify(deviceNumberDao, times(1)).selectPage(any(), any(QueryWrapper.class));
    }

    @Test
    void listDeviceNumbersByBatchId_WithValidBatchId_ReturnsList() {
        // Given
        String batchId = "batch1";
        DeviceNumberEntity number1 = new DeviceNumberEntity();
        number1.setId("number1");
        number1.setBatchId(batchId);
        number1.setDeviceNumber("1234567890");

        when(deviceNumberDao.selectList(any(QueryWrapper.class))).thenReturn(Arrays.asList(number1));

        // When
        List<DeviceNumberEntity> result = deviceNumberService.listDeviceNumbersByBatchId(batchId);

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("1234567890", result.get(0).getDeviceNumber());
        verify(deviceNumberDao, times(1)).selectList(any(QueryWrapper.class));
    }
}