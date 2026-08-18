# 调查员创建

1. 读取战役规则档案并确认 Classic/Pulp、时代、可选规则和职业来源。
2. 通过 CLI 生成或验证 STR、CON、SIZ、DEX、APP、INT、POW、EDU 与 Luck。
3. 计算 HP、MP、SAN、SAN 上限、MOV、DB 和 Build，并保留年龄调整。
4. 选择职业，记录信用评级范围，分配职业与兴趣技能点。
5. 选择本职技能、战斗技能、语言、财产、装备、重要人物、信念、地点、珍贵物品、
   特征、伤疤/恐惧与背景关系。
6. Pulp 调查员再处理原型、天赋、更高 HP 与相应可选规则。
7. 展示完整草稿和派生值，等待玩家最终确认；确认前不得持久化。
8. 创建后重新读取并验证技能点、HP/MP/SAN/Luck、DB/Build、MOV 和玩家绑定。

成长必须增量修改现有调查员：逐项执行技能成长检定、Luck 恢复、年龄变化、治疗、
疯狂与 Mythos 导致的变更，记录事件并在结束时创建 Snapshot。

```powershell
sagasmith-coc investigator create --campaign <id> --name "<name>" --player "<player>" --sheet '<json>' --json
```

不得在玩家确认前持久化草稿。
