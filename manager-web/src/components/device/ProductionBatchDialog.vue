<template>
  <el-dialog :visible="dialogVisible" @update:visible="handleVisibleChange" width="50%" center
    custom-class="custom-dialog" :show-close="false" class="center-dialog">
    <div style="margin: 0 18px; text-align: left; padding: 10px; border-radius: 10px;">
      <div style="font-size: 30px; color: #3d4566; margin-top: -10px; margin-bottom: 10px; text-align: center;">
        {{ editMode ? '编辑生产批次' : '添加生产批次' }}
      </div>

      <button class="custom-close-btn" @click="handleClose">
        ×
      </button>

      <div style="height: 2px; background: #e9e9e9; margin-bottom: 22px;"></div>
      <el-form :model="formData" label-width="100px" label-position="left" class="custom-form">
        <div style="display: flex; gap: 20px; margin-bottom: 0;">
          <el-form-item label="工厂ID" prop="factoryId" style="flex: 1;">
            <el-input v-model.number="formData.factoryId" placeholder="请输入工厂ID" class="custom-input-bg" :disabled="editMode"></el-input>
          </el-form-item>
          <el-form-item label="型号" prop="modelType" style="flex: 1;">
            <el-input v-model="formData.modelType" placeholder="请输入型号" class="custom-input-bg" :disabled="editMode"></el-input>
          </el-form-item>
        </div>

        <div style="display: flex; gap: 20px; margin-bottom: 0;">
          <el-form-item label="生产日期" prop="productionDate" style="flex: 1;">
            <el-date-picker
              v-model="formData.productionDate"
              type="date"
              placeholder="请选择生产日期"
              format="yyyy-MM-dd"
              value-format="yyyy-MM-dd"
              class="custom-input-bg"
              style="width: 100%;"
              :disabled="editMode">
            </el-date-picker>
          </el-form-item>
          <el-form-item label="硬件版本" prop="hardwareVersion" style="flex: 1;">
            <el-input v-model="formData.hardwareVersion" placeholder="请输入硬件版本" class="custom-input-bg" :disabled="editMode"></el-input>
          </el-form-item>
        </div>

        <div style="display: flex; gap: 20px; margin-bottom: 0;">
          <el-form-item label="代理商编码" prop="agentCode" style="flex: 1;">
            <el-input v-model="formData.agentCode" placeholder="请输入代理商编码" class="custom-input-bg" :disabled="editMode"></el-input>
          </el-form-item>
          <el-form-item label="状态" prop="status" style="flex: 1;">
            <el-select v-model="formData.status" placeholder="请选择状态" class="custom-select custom-input-bg" style="width: 100%;" :disabled="editMode">
              <el-option label="待生产" :value="0"></el-option>
              <el-option label="生产中" :value="1"></el-option>
              <el-option label="已生产" :value="2"></el-option>
              <el-option label="已作废" :value="3"></el-option>
            </el-select>
          </el-form-item>
        </div>

        <div style="display: flex; gap: 20px; margin-bottom: 0;">
          <el-form-item label="开始序号" prop="startSerialNumber" style="flex: 1;">
            <el-input v-model.number="formData.startSerialNumber" placeholder="请输入开始序号" class="custom-input-bg" :disabled="editMode"></el-input>
          </el-form-item>
          <el-form-item label="结束序号" prop="endSerialNumber" style="flex: 1;">
            <el-input v-model.number="formData.endSerialNumber" placeholder="请输入结束序号" class="custom-input-bg" :disabled="editMode"></el-input>
          </el-form-item>
        </div>

      </el-form>
    </div>

    <div style="display: flex;justify-content: center;">
      <el-button
        type="primary"
        @click="confirm"
        class="save-btn"
        :loading="saving"
        :disabled="saving">
        保存
      </el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'ProductionBatchDialog',
  props: {
    visible: { type: Boolean, required: true },
    data: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      saving: false,
      dialogVisible: false,
      formData: {
        factoryId: null,
        modelType: '',
        productionDate: '',
        hardwareVersion: '',
        agentCode: '',
        status: 0,
        startSerialNumber: null,
        endSerialNumber: null
      }
    }
  },
  computed: {
    editMode() {
      return !!this.data.id;
    }
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
      if (val) {
        if (this.editMode) {
          this.formData = { ...this.data };
        } else {
          this.resetForm();
          if (this.data.factoryId) {
            this.formData.factoryId = this.data.factoryId;
          }
        }
      } else {
        this.resetForm();
      }
    }
  },
  methods: {
    handleVisibleChange(val) {
      this.dialogVisible = val;
      this.$emit('update:visible', val);
    },

    handleClose() {
      this.saving = false;
      this.$emit('update:visible', false);
    },

    confirm() {
      this.saving = true;
      try {
        // Validate serial numbers if provided
        if (this.formData.startSerialNumber !== null && this.formData.endSerialNumber !== null) {
          if (this.formData.startSerialNumber >= this.formData.endSerialNumber) {
            this.$message.error('开始序号必须小于结束序号');
            this.saving = false;
            return;
          }
        }
        this.$emit('save', { ...this.formData });
        this.$emit('update:visible', false);
      } catch (e) {
        console.error(e);
      } finally {
        this.saving = false;
      }
    },

    resetForm() {
      this.saving = false;
      this.formData = {
        factoryId: null,
        modelType: '',
        productionDate: '',
        hardwareVersion: '',
        agentCode: '',
        status: 0,
        startSerialNumber: null,
        endSerialNumber: null
      };
    }
  }
}
</script>

<style scoped>
.custom-dialog {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  background: white;
  padding-bottom: 17px;
}

.custom-dialog .el-dialog__header {
  padding: 0;
  border-bottom: none;
}

.center-dialog {
  display: flex;
  align-items: center;
  justify-content: center;
}

.center-dialog .el-dialog {
  margin: 0 0 auto !important;
  display: flex;
  flex-direction: column;
}

.custom-close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 35px;
  height: 35px;
  border-radius: 50%;
  border: 2px solid #cfcfcf;
  background: none;
  font-size: 30px;
  font-weight: lighter;
  color: #cfcfcf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  padding: 0;
  outline: none;
}

.custom-close-btn:hover {
  color: #409EFF;
  border-color: #409EFF;
}

.custom-select .el-input__suffix {
  background: #e6e8ea;
  right: 6px;
  width: 20px;
  height: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  top: 9px;
}

.custom-select .el-input__suffix-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.custom-select .el-icon-arrow-up:before {
  content: "";
  display: inline-block;
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 7px solid #c0c4cc;
  position: relative;
  top: -2px;
  transform: rotate(180deg);
}

.custom-form .el-form-item {
  margin-bottom: 20px;
}

.custom-form .el-form-item__label {
  color: #3d4566;
  font-weight: normal;
  text-align: right;
  padding-right: 20px;
}

.custom-input-bg .el-input__inner::-webkit-input-placeholder,
.custom-input-bg .el-textarea__inner::-webkit-input-placeholder {
  color: #9c9f9e;
}

.custom-input-bg .el-input__inner,
.custom-input-bg .el-textarea__inner {
  background-color: #f6f8fc;
}

.save-btn {
  background: #e6f0fd;
  color: #237ff4;
  border: 1px solid #b3d1ff;
  width: 150px;
  height: 40px;
  font-size: 16px;
  transition: all 0.3s ease;
}

.save-btn:hover {
  background: linear-gradient(to right, #237ff4, #9c40d5);
  color: white;
  border: none;
}

.custom-switch .el-switch__core {
  border-radius: 20px;
  height: 23px;
  background-color: #c0ccda;
  width: 35px;
  padding: 0 20px;
}

.custom-switch .el-switch__core:after {
  width: 15px;
  height: 15px;
  background-color: white;
  top: 3px;
  left: 4px;
  transition: all .3s;
}

.custom-switch.is-checked .el-switch__core {
  border-color: #b5bcf0;
  background-color: #cfd7fa;
  padding: 0 20px;
}

.custom-switch.is-checked .el-switch__core:after {
  left: 100%;
  margin-left: -18px;
  background-color: #1b47ee;
}

[style*="display: flex"] {
  gap: 20px;
}

.custom-input-bg .el-input__inner {
  height: 32px;
}
</style>