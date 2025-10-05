---
description: 生成小红书单个帖子
tool:
  tool_id: TEMPLATE
input_description:
  human_setup: 小红书的账号人设
  post_target_audience: 干货贴的对象
  topic: 小红书帖子的主题
  emotion_target: 当前帖子需要重点刺激的受众情感共鸣点
input_json_path:
  current_task: $.current_task
  human_setup: $.blog_human_setup
  post_target_audience: $.blog_post_target_audience
output_description: 干货贴的生成方案
result_validation_rule: 需要有小红书帖子的文字内容以及图片（url 或本地路径皆可)。
---
## Execution Plan

<new task to execute>
1. 根据文档 write_xiaohongshu_post_text.md, 为 {human_setup} 的博主，写一篇给 {post_target_audience} 看的，关于{topic}的干货帖子，情感共鸣点：{emotion_target}。
2. 根据文档 llm.md，为前面写好的这篇帖子设计一个小红书帖子的封面图（文字描述），封面图的描述不超过200字。封面要符合小红书爆款帖子的样子。小红书封面上的文字是帖子的结论和精华，只出现3-10个字即可。封面图片通常色彩鲜艳、明亮、对比度高。“手帐感”和“涂鸦感”十足，加圈画框：用不同颜色的画笔框出重点，像老师划重点一样。使用手绘箭头：指引视线，告诉你先看哪里，后看哪里。使用可爱的贴纸和Emoji：✨ Bling Bling的星星、❤️爱心、🔥火焰等，用来烘托氛围和情绪。使用手写字体：使用可爱、随性的手写字体，增加亲切感。
3. 根据文档 generate_seed_dream_pic.md，为前面写好的这篇帖子生成一个首页的封面图。
</new task to execute>