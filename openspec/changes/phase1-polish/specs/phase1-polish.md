# Spec Delta: Phase 1 基础体验打磨

## ADDED: Hero Banner 精选路线
- 发现页顶部新增 Hero Banner 轮播区域
- 后端 `GET /routes/featured` 返回 `is_featured=true` 的路线（最多 5 条）
- 16:9 横滑卡片 4 秒自动轮播，手动滑动可打断
- 无精选路线时隐藏，不展示空白区域

## ADDED: 路线卡片视觉升级
- `preview_image` 非空时显示真实封面缩略图
- 无封面时根据 `route.name` 哈希生成唯一渐变色占位图（12 色调色板）
- 按压动效：scale 0.97 → spring 回弹

## ADDED: 路线编辑页
- `EditRouteView`：编辑名称/描述/难度/标签/城市/封面图
- 封面图通过 PHPicker 选图 → Base64 → `POST /routes/{id}/cover` 上传
- 信息编辑通过 `PUT /routes/{id}` 更新
- 仅路线创建者可编辑

## ADDED: 分享卡片
- `ShareCardView` 生成 300pt 宽路线信息卡片
- `ImageRenderer` 截图 → `PHPhotoLibrary` 保存到相册
- Toast 提示保存成功

## MODIFIED: 空状态引导
- 个人中心无路线时：插画 + 副标题 + "去记录第一条路线"CTA 按钮
- 发现页搜索无结果时：展示 3 条热门路线小卡片推荐
