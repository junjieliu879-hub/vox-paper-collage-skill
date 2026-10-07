# 来源与发布范围

本仓库由 junjieliu879-hub 发布，整理本地 Vox 式剪纸拼贴工作流。它不是 Vox Media 官方项目，也不代表与 Vox Media 存在隶属关系。

## 上游

参考 [Alisa0808/vox-director](https://github.com/Alisa0808/vox-director)，本地安装快照版本 1.0.0。`upstream-prompt-guide.md`、`upstream-beat-layer.md`、`upstream-local-engine.md` 保留自该快照，适用原作者 Alisa Qian 的 MIT 许可证，全文见 LICENSE-UPSTREAM。
本地工作流的整理文档也参考了该方法，因此分发本仓库时同时保留 LICENSE 与 LICENSE-UPSTREAM。我们增加了图片素材与本地渲染的交接规则、实际案例代码和不含外部媒体的机制演示。没有声明发明所有上游方法。

上游文档中的云服务、配音或音乐步骤不是本仓库必需依赖；它们仅供溯源和按需阅读。当前默认是图片生成编辑 + Canvas/Chrome 或 Pillow + FFmpeg。

## 不在公开仓库中的文件

- 私人交接包、用户原声/歌曲、案例配音、历史成片和检查截图。
- 授权尚未逐项确认的案例生成图片。
- 私人路径、聊天记录、账号凭据、商业字体、node_modules 和模型缓存。

`demo.html` 仅由本仓库代码绘制，无上述媒体依赖。案例代码需要使用者自行生成或提供有权使用的素材；规格见 ASSETS.json。MIT 授权不自动覆盖使用者后来添加的图像、音频、字体和第三方模型输出。
