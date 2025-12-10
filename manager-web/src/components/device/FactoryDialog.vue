<template>
  <el-dialog :visible="dialogVisible" @update:visible="handleVisibleChange" width="50%" center
    custom-class="custom-dialog" :show-close="false" class="center-dialog">
    <div style="margin: 0 18px; text-align: left; padding: 10px; border-radius: 10px;">
      <div style="font-size: 30px; color: #3d4566; margin-top: -10px; margin-bottom: 10px; text-align: center;">
        {{ editMode ? '编辑工厂' : '添加工厂' }}
      </div>

      <button class="custom-close-btn" @click="handleClose">
        ×
      </button>

      <div style="height: 2px; background: #e9e9e9; margin-bottom: 22px;"></div>
      <el-form :model="formData" label-width="100px" label-position="left" class="custom-form">
        <div style="display: flex; gap: 20px; margin-bottom: 0;">
          <el-form-item label="工厂名称" prop="name" style="flex: 1;">
            <el-input v-model="formData.name" placeholder="请输入工厂名称" class="custom-input-bg"></el-input>
          </el-form-item>
          <el-form-item label="工厂编号" prop="code" style="flex: 1;">
            <el-input v-model="formData.code" placeholder="请输入工厂编号" class="custom-input-bg"></el-input>
          </el-form-item>
        </div>

        <div style="display: flex; gap: 20px; margin-bottom: 0;">
          <el-form-item label="国家" prop="country" style="flex: 1;">
            <el-input v-model="formData.country" placeholder="请输入国家编号(如86)" class="custom-input-bg"></el-input>
          </el-form-item>
          <el-form-item label="状态" prop="status" style="flex: 1;">
            <el-select v-model="formData.status" placeholder="请选择状态" class="custom-select custom-input-bg" style="width: 100%;">
              <el-option label="启用" :value="0"></el-option>
              <el-option label="禁用" :value="1"></el-option>
            </el-select>
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
  name: 'FactoryDialog',
  props: {
    visible: { type: Boolean, required: true },
    data: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      saving: false,
      dialogVisible: false,
      formData: {
        id: undefined,
        name: '',
        code: '',
        country: '',
        status: 0
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
        // 数据验证
        if (!this.formData.name) {
          this.$message.warning('请输入工厂名称');
          this.saving = false;
          return;
        }
        if (!this.formData.code) {
          this.$message.warning('请输入工厂编号');
          this.saving = false;
          return;
        }
        if (!this.formData.country) {
          this.$message.warning('请输入国家');
          this.saving = false;
          return;
        }
        
        this.$emit('save', { ...this.formData });
        this.$emit('update:visible', false);
      } catch (e) {
        console.error(e);
        this.$message.error('保存失败');
      } finally {
        this.saving = false;
      }
    },

    resetForm() {
      this.saving = false;
      this.formData = {
        id: undefined,
        name: '',
        code: '',
        country: '',
        status: 0
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