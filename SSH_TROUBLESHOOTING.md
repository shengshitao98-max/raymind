# SSH 连接故障排除指南

## 问题描述

用户尝试通过 SSH 连接到树莓派，但遇到以下问题：

```
ssh pi@10.108.29.135  
The authenticity of host '10.108.29.135 (10.108.29.135)' can't be established. 
ED25519 key fingerprint is SHA256:OrZywGbovdlQ0X2LGZqVirf50vJKwHVIj4AWGp1ab4M. 
This key is not known by any other names 
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

输入密码后：

```
pi@10.108.29.135's password: 
Permission denied, please try again.
```

## 解决方案

### 1. 确认 IP 地址

从热点连接列表中可以看到，树莓派已成功连接，IP 地址为 `10.108.29.135`。

### 2. 默认用户名和密码

根据系统类型，默认用户名不同：

| 系统类型 | 默认用户名 | 默认密码 |
|---------|-----------|----------|
| Raspberry Pi OS | pi | raspberry |
| Ubuntu Server | ubuntu | ubuntu |
| Jetson Nano | jetson | nvidia |

### 3. 首次连接确认

当首次连接时，会出现密钥确认提示，这是正常的安全机制。输入 `yes` 即可。

### 4. 常见问题及解决方案

#### 问题 1：密码错误

**原因**：使用了错误的密码或用户名

**解决方案**：
- 尝试不同的默认密码组合
- 确认使用了正确的用户名
- 如果忘记密码，需要重新烧录系统

#### 问题 2：SSH 服务未启用

**原因**：系统未启用 SSH 服务

**解决方案**：
1. 重新烧录系统，在 Raspberry Pi Imager 中启用 SSH
2. 或在启动时创建 `ssh` 文件：
   - 挂载 TF 卡到电脑
   - 在 boot 分区创建一个名为 `ssh` 的空文件
   - 重新插入 TF 卡到树莓派并启动

#### 问题 3：网络连接问题

**原因**：网络连接不稳定或 IP 地址变化

**解决方案**：
- 确认树莓派已连接到热点
- 检查网络连接稳定性
- 尝试使用固定 IP 地址

### 5. 连接步骤

1. **确认树莓派已启动并连接到网络**
   - 从热点连接列表中确认 IP 地址

2. **打开终端或 SSH 客户端**
   - Windows：使用 PuTTY
   - Linux/Mac：使用终端

3. **尝试不同的用户名**

   ```bash
   # 尝试 Raspberry Pi OS 默认用户
   ssh pi@10.108.29.135
   # 密码: raspberry

   # 尝试 Ubuntu 默认用户
   ssh ubuntu@10.108.29.135
   # 密码: ubuntu

   # 尝试 Jetson 默认用户
   ssh jetson@10.108.29.135
   # 密码: nvidia
   ```

4. **首次连接时输入 yes**

   ```
   Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
   ```

5. **输入密码**

### 6. 重置密码

如果忘记密码，需要重新烧录系统：

1. 使用 Raspberry Pi Imager 重新烧录
2. 在高级设置中设置新的用户名和密码
3. 启用 SSH
4. 配置 WiFi（可选）

### 7. 验证连接

成功连接后，可以运行以下命令验证：

```bash
# 检查系统信息
uname -a

# 检查 ROS2 版本
ros2 --version

# 检查网络配置
ifconfig
```

## 快速命令

```bash
# 尝试所有可能的用户名
ssh pi@10.108.29.135       # 密码: raspberry
ssh ubuntu@10.108.29.135   # 密码: ubuntu
ssh jetson@10.108.29.135   # 密码: nvidia
```

## 注意事项

1. **安全提示**：首次连接后应立即修改默认密码
2. **网络设置**：确保电脑和树莓派在同一网络
3. **防火墙**：检查是否有防火墙阻止 SSH 连接
4. **电源**：确保树莓派供电稳定

## 联系支持

如果以上方法都无法解决问题，请参考：
- [Raspberry Pi SSH 文档](https://www.raspberrypi.com/documentation/computers/remote-access.html#ssh)
- [Ubuntu SSH 指南](https://ubuntu.com/server/docs/openssh-server)

---

*文档版本: 1.0*
*更新日期: 2026-04-11*