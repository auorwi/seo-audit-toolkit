# 语言与地区数据

`data/language-subtag-registry.txt`为IANA原始注册表快照，File-Date 2026-08-08；抓取来源、时间、SHA256见registry-source.json。

`data/iso3166-1.json`为pycountry维护的ISO国家数据原始JSON，249条；来源、抓取时间和SHA256见country-source.json。它是维护者的数据快照，不是实时ISO认证服务，也不等于IANA全部region记录。文件未修改。

[IANA注册表](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry) · [pycountry项目](https://github.com/pycountry/pycountry) · [数据原文件](https://raw.githubusercontent.com/pycountry/pycountry/main/src/pycountry/databases/iso3166-1.json)。pycountry项目提供LGPL2.1许可证，原文随包保留在data/pycountry-LICENSE.txt；其数据来源基于iso-codes。维护者及上游的权利与原许可保留，本技能不对该数据作独占权利主张。

规范或数据升级时先保存新原文件/来源/hash并复跑代码、区域、脚本及弃用项测试，再替换快照；不能只更新JSON声明的日期。
