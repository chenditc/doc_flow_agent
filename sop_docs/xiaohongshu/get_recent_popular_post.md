---
description: 搜索并获取一定时间范围的小红书笔记信息
tool:
  tool_id: PYTHON_EXECUTOR
  parameters:
    task_description: "请按当前任务的要求填入需要过滤的笔记条件，并返回笔记的标题、封面、链接、正文、博主名、粉丝数等信息。"
input_description:
  related_context_content: 需要过滤的笔记条件。如：关键词、时间范围、分类。如果没有特殊说明，时间范围使用 24h 以内。如果没有特殊要求，分类可以不填。
output_description: 爆款笔记信息，包括标题、封面、链接、正文、博主名、粉丝数等信息，按用户要求的格式返回。如果没有特殊要求，则按示例格式返回。
skip_new_task_generation: true
result_validation_rule: xiaohongshu post info as a list of dict, empty list if fine as long as there is no error or exception.
---
## 该 API 调用前需要 login

使用下面这个 login api 进行登陆并保存 session

curl 'https://gw.newrank.cn/api/xh/xdnphb/nr/app/xhs/user/login' \
  -H 'Accept: */*' \
  -H 'Accept-Language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,zh-TW;q=0.6' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -b "$COOKIE_FOR_NEWRANK" \
  -H 'Origin: https://xh.newrank.cn' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://xh.newrank.cn/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-site' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -H 'content-type: application/json' \
  -H 'n-token: 35c430ef650b459ba2b9c1409148d929' \
  -H 'sec-ch-ua: "Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --data-raw '{"fromUrl":"https://xh.newrank.cn/notes/notesSearch","unit":"","keyword":"","type":"","bridgeCode":null}'

你会得到类似这个响应：

{"msg":"","data":{"headImgUrl":"http://thirdwx.qlogo.cn/mmopen/sXCkKk1ibZUvq1VHfvZiahbNJfojfzZpGejN1LiaDa9EqyzdYOUfcVro7TgURrmRTq1icyMezKCfib8SFicKibsCMPoKIa2Gt6KMOGL/132","nickName":"三鹿","vipLevel":2,"vipEndTime":"2025-11-10 11:05:53","type":0,"mainUserName":"凡弟","now":"2025-11-03 20:13:50","userType":0,"shareCount":null,"shareTotal":null,"vipType":1,"isSuper":false,"levelName":null,"nrId":"nr_9r18hyh9p","gmtCreate":"2023-10-23 11:08:19","isNew":null,"fromType":null,"vipEndDay":7},"code":2000}

检查 vipEndTime 并保证这个值大于 now，否则需要报错。

## 该 API 的 curl 调用示例

COOKIE_FOR_NEWRANK 可以从环境变量获取。

互动量 (Interaction Metrics): 除非用户有特殊要求，否则使用 点赞数 >= 100。。
排序方式 (Sorting): 按点赞数 (likedCount) 排序。

curl 'https://gw.newrank.cn/api/xh/xdnphb/nr/app/xhs/note/search' \
  -H 'Accept: */*' \
  -H 'Accept-Language: en-US,en;q=0.9' \
  -H 'Connection: keep-alive' \
  -b '$COOKIE_FOR_NEWRANK' \
  -H 'Origin: https://xh.newrank.cn' \
  -H 'Referer: https://xh.newrank.cn/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-site' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -H 'content-type: application/json' \
  -H 'n-token: 35c430ef650b459ba2b9c1409148d929' \
  -H 'request_id: f494d9d9172848fd90c6422df9c4bb1f' \
  -H 'sec-ch-ua: "Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --data-raw '{"input":{"keyword":"作文","type":["title","topic","content","tag","name","categoryName","seedBrandName"]},"baseInfoRequest":{"type":"","createTime":"24h","contentTags":[],"noteType":"","startTime":"","endTime":"","commentFeature":"0","firstType":"教育","secondType":"中学教育"},"high":{"isMcn":"","authorGender":"","userAttribute":[],"fan":{"fixedRange":"","customizeRange":""},"likedCollectedCountRange":{"fixedRange":"","customizeRange":""},"interactiveCountRange":{"fixedRange":"","customizeRange":""},"likedCountRange":{"fixedRange":"","customizeRange":"100-"},"collectedCountRange":{"fixedRange":"","customizeRange":""},"commentsCountRange":{"fixedRange":"","customizeRange":""},"sharedCountRange":{"fixedRange":"","customizeRange":""},"predReadnumRange":{"fixedRange":"","customizeRange":""},"province":"","city":""},"sort":"likedCount","size":20,"start":1,"custom":{"must":[],"should":[],"mustNot":[]},"source":{"type":"","keyword":""},"time":"24h","startTime":"","endTime":"","filterIncomplete":0}'

Example response:

{
    "code": 2000,
    "data": {
        "count": 1,
        "list": [
            {
                "accountTypeV1": null,
                "anaTime": "2025-10-21 11:45:22",
                "businessNotePrice": null,
                "categoryName": null,
                "city": null,
                "collectedCount": "262",
                "collectionTime": null,
                "comments": null,
                "commentsCount": "62",
                "cooperateBindsId": null,
                "cooperateBindsName": null,
                "cover": "http://sns-img-hw.xhscdn.net/1040g2sg31ns3hpdul8gg5q4dcf7q5er3b7ooe20?imageView2/2/w/1080/format/webp",
                "coverUrl": "http://sns-img-hw.xhscdn.net/1040g2sg31ns3hpdul8gg5q4dcf7q5er3b7ooe20?imageView2/2/w/1080/format/webp",
                "createTime": "2025-10-20T13:01:05.000+0000",
                "currentFans": null,
                "desc": "年年押，年年中❗\n七上期中考试就要来了\n这是火箭班老师给的期中考试<span class=\"xr_highlight\">作文</span>押题\n次次都中，所以期中<span class=\"xr_highlight\">作文</span>一定从这出\n此帖不删，等娃娃们考完回来报喜～\n\t\n<span class=\"xr_highlight\">作文</span>占总分值的半壁江山\n<span class=\"xr_highlight\">作文</span>有把握，语文才能考高分\n我们火箭班老师翻遍近几年的期中卷➕名校真题卷\n发现期中考试的<span class=\"xr_highlight\">作文</span>无非就三类\n1️⃣写人\n2️⃣写景\n3️⃣写感悟\n\t\n老师们熬夜整理出来15篇范文母素材\n不管题目怎么变，套这几篇都能用❗\n从今天开始每天熟读1篇\n考前刚好看完➕消化\n<span class=\"xr_highlight\">作文</span>不慌，直接逆袭前三❗\n\t\n#家长收藏孩子受益 #七年级上册 #<span class=\"xr_highlight\">作文</span>模板 #七上语文 #期中 #学渣逆袭 #<span class=\"xr_highlight\">作文</span>押题 #提高孩子学习成绩 #期中押题 #期中考试",
                "discernBusinessBrandId": null,
                "discernBusinessBrandName": null,
                "firstFrameUrl": "https://sns-na-i3.xhscdn.com/1040g2sg31ns3hpdul8gg5q4dcf7q5er3b7ooe20?imageView2/2/w/540/format/webp%7CimageMogr2/strip&redImage/frame/0&ap=12&sc=USR_PRV&sign=bead1ce6551562f817335a82f2fd2180&t=68f7019a",
                "id": "68f632910000000005011161",
                "interactiveCount": "534",
                "ipLocationStandardization": null,
                "isCooperate": null,
                "isDelete": 0,
                "isVisible": 0,
                "likedCollectedCount": "472",
                "likedCount": "210",
                "maxCommentNum": 0,
                "nomal": true,
                "noteCounterTypeV1": "教育",
                "noteCounterTypeV2": "中学教育",
                "officialKeyword": [
                    "期中",
                    "作文押题",
                    "作文模板",
                    "期中考试",
                    "七上语文",
                    "学渣逆袭",
                    "期中押题",
                    "七年级上册",
                    "教育",
                    "中学教育"
                ],
                "pgyFeaturetags": null,
                "picturePrice": null,
                "picturePricePredict": null,
                "poi": null,
                "predReadnum": "16578",
                "price": null,
                "province": null,
                "readCount": "16578",
                "readedCount": null,
                "redId": null,
                "seedBrandId": null,
                "seedBrandName": null,
                "seedCooperateId": null,
                "seedCooperateName": null,
                "sharedCount": "69",
                "shareLink": null,
                "title": "七上语文期中考试<span class=\"xr_highlight\">作文</span>押题❗就这15篇，背吧❗",
                "topics": [
                    {
                        "name": "家长收藏孩子受益"
                    },
                    {
                        "name": "七年级上册"
                    },
                    {
                        "name": "作文模板"
                    },
                    {
                        "name": "七上语文"
                    },
                    {
                        "name": "期中"
                    },
                    {
                        "name": "学渣逆袭"
                    },
                    {
                        "name": "作文押题"
                    },
                    {
                        "name": "提高孩子学习成绩"
                    },
                    {
                        "name": "期中押题"
                    },
                    {
                        "name": "期中考试"
                    }
                ],
                "type": "normal",
                "url": null,
                "user": {
                    "accountTypeV1": "教育",
                    "accountTypeV2": "中学教育",
                    "fans": 4350,
                    "image": null,
                    "images": "https://sns-avatar-qc.xhscdn.com/avatar/69275234-c05c-393d-b7f5-01f857401b27?imageView2/2/w/540/format/webp",
                    "nickname": "秋棠老师爱分享-极简",
                    "redId": "18972069848",
                    "redOfficialVerifyType": null,
                    "userAttribute": 7,
                    "userid": "688d63cf000000002802bb63"
                },
                "userid": null,
                "videoInfo": null,
                "videoPrice": null,
                "videoPricePredict": null
            }
        ],
        "resultCount": "1",
        "total": 500,
        "update_time": "2025-10-21 20:53:20"
    },
    "msg": ""
}

Note: Need to check the 'code' field is 2000 to ensure the response is successful.

## 返回内容

如果用户没有特殊要求，则使用下列格式返回，如果有特殊要求，则按用户要求返回。

[
    {
        "title": "笔记标题",
        "cover": "笔记封面图片链接",
        "link": "笔记链接",
        "content": "笔记正文内容",
        "create_time": "发布时间",
        "share_count": "分享次数",
        "liked_count": "点赞次数",
        "collected_count": "收藏次数",
        "comments_count": "评论次数",
        "author_name": "博主名称",
        "author_fans": "博主粉丝数",
        "author_link": "博主主页链接"
    }
]

笔记标题：从 response 中的 data.list[*].title 获取
笔记封面图片链接：从 response 中的 data.list[*].coverUrl 获取
笔记链接：格式为 https://www.xiaohongshu.com/explore/{note_id}，其中 note_id 从 response 中的 data.list[*].id 获取
笔记正文内容：从 response 中的 data.list[*].desc 获取
博主名称：从 response 中的 data.list[*].user.nickname 获取
博主粉丝数：从 response 中的 data.list[*].user.fans 获取
笔记发布时间：从 response 中的 data.list[*].createTime 获取
分享次数：从 response 中的 data.list[*].sharedCount 获取
点赞次数：从 response 中的 data.list[*].likedCount 获取
收藏次数：从 response 中的 data.list[*].collectedCount 获取
评论次数：从 response 中的 data.list[*].commentsCount 获取