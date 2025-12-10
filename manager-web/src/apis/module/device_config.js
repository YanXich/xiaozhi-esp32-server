import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

export default {
    // 工厂管理相关接口
    getFactories(params, callback) {
        // console.log(`${getServiceUrl()}/device-management/factories`);
        // console.log(params);
        const queryParams = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/factories?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取参数列表失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getFactories(params, callback)
                })
            }).send()
    },
    
    createFactory(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/factory`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('创建工厂失败:', err);
                RequestService.reAjaxFun(() => {
                    this.createFactory(data, callback);
                });
            }).send();
    },
    
    updateFactory(id, data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/factory/${id}`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('更新工厂失败:', err);
                RequestService.reAjaxFun(() => {
                    this.updateFactory(id, data, callback);
                });
            }).send();
    },
    
    // 车型配置相关接口
    getCarModels(params, callback) {
        const queryParams = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/car-models?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取车型配置列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getCarModels(params, callback);
                });
            }).send();
    },
    
    createCarModel(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/car-model`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('创建车型配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.createCarModel(data, callback);
                });
            }).send();
    },
    
    updateCarModel(id, data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/car-model/${id}`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('更新车型配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.updateCarModel(id, data, callback);
                });
            }).send();
    },
    
    deleteCarModel(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/car-model/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('删除车型配置失败:', err);
                RequestService.reAjaxFun(() => {
                    this.deleteCarModel(id, callback);
                });
            }).send();
    },
    
    // 生产批次相关接口
    getProductionBatches(params, callback) {
        const queryParams = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/batches?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取生产批次列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getProductionBatches(params, callback);
                });
            }).send();
    },
    
    createProductionBatch(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/batch`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('创建生产批次失败:', err);
                RequestService.reAjaxFun(() => {
                    this.createProductionBatch(data, callback);
                });
            }).send();
    },
    
    // 设备号管理相关接口
    getDeviceNumbersByBatch(batchId, params, callback) {
        const queryParams = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/device-numbers/${batchId}?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取设备号列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getDeviceNumbers(batchId, params, callback);
                });
            }).send();
    },

    // 设备号管理相关接口
    getDeviceNumbers(params, callback) {
        const queryParams = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/device-numbers?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取设备号列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getDeviceNumbers(params, callback);
                });
            }).send();
    },
    
    // 设备号状态更新接口
    updateDeviceNumberStatus(id, status, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/device-number/${id}/status/${status}`)
            .method('PUT')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('更新设备号状态失败:', err);
                RequestService.reAjaxFun(() => {
                    this.updateDeviceNumberStatus(id, status, callback);
                });
            }).send();
    },

    // 设备MAC相关接口
    getDeviceConfigs(params, callback) {
        const queryParams = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/device-macs?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取设备MAC列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getDeviceConfigs(params, callback);
                });
            }).send();
    },

    createDeviceConfig(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/device-mac`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('创建设备MAC失败:', err);
                RequestService.reAjaxFun(() => {
                    this.createDeviceConfig(data, callback);
                });
            }).send();
    },

    getDeviceConfigById(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/device-mac/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取设备MAC详情失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getDeviceConfigById(id, callback);
                });
            }).send();
    },

    updateDeviceConfig(id, data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/device-mac/${id}`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('更新设备MAC失败:', err);
                RequestService.reAjaxFun(() => {
                    this.updateDeviceConfig(id, data, callback);
                });
            }).send();
    },

    deleteDeviceConfig(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/device-management/device-mac/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('删除设备MAC失败:', err);
                RequestService.reAjaxFun(() => {
                    this.deleteDeviceConfig(id, callback);
                });
            }).send();
    },
}