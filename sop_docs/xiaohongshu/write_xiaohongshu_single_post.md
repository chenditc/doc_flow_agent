---
description: 生成小红书单个帖子
tool:
  tool_id: TEMPLATE
input_description:
  human_setup: 小红书的账号人设
  post_target_audience: 小红书贴的对象
  topic: 小红书帖子的主题
  emotion_target: 当前帖子需要重点刺激的受众情感共鸣点
input_json_path:
  current_task: $.current_task
  human_setup: $.blog_human_setup
  post_target_audience: $.blog_post_target_audience
output_description: 小红书贴的生成方案
result_validation_rule: 需要有小红书帖子的文字内容以及图片（url 或本地路径皆可)。
---
## Execution Plan

<new task to execute>
1. 根据文档 write_xiaohongshu_post_text.md, 为 {human_setup} 的博主，写一篇给 {post_target_audience} 看的，关于{topic}的帖子，情感共鸣点：{emotion_target}。
</new task to execute>
<new task to execute>
2. 根据文档 llm.md，为前面写好的这篇帖子设计3个小红书帖子的封面图（文字描述），封面图的描述不超过50字。封面要符合小红书爆款帖子的样子。小红书封面上的文字是只出现3-20个字即可，可以是一句日常、有活人感的问句或者祈使句，例如“不要再团购舞蹈课了！”,“为什么说AI是百年一遇的机会？”。文字出现在图片正中间。封面图片通常用色简单（不超过3种颜色）、色彩鲜艳但饱和度低。“手帐感”和“涂鸦感”十足，加圈画框：用不同颜色的画笔框出一个重点，像老师划重点一样。使用手写字体：使用可爱、随性的手写字体，增加亲切感。需要出现的文字用引号标注“”。

例如：奶油米+雾蓝+暖橙，格纸底；手写体标题，用橙圈箭头指向一个小闹钟，突出15分钟的感觉。角落有几个星星涂鸦。图片正中用可爱、随性的手写字体写着 “有没有娃写作文的时候就脑子空空的？”
</new task to execute>
<new task to execute>
3. 根据文档 generate_seed_dream_pic.md，使用前一步生成的封面图描述文字作为提示词，使用前面的3个提示词生成3张封面图。
</new task to execute>