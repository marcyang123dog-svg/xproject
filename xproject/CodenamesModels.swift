//
//  CodenamesModels.swift
//  xproject
//

import Foundation

enum CardColor: CaseIterable {
    case red, blue, neutral, assassin

    var displayName: String {
        switch self {
        case .red: return "红队"
        case .blue: return "蓝队"
        case .neutral: return "旁观者"
        case .assassin: return "刺客"
        }
    }
}

enum Team {
    case red, blue

    var displayName: String { self == .red ? "红队" : "蓝队" }
    var opposite: Team { self == .red ? .blue : .red }
}

enum GameState {
    case playing
    case redWins
    case blueWins
    case assassinRevealed(by: Team)

    var isOver: Bool {
        if case .playing = self { return false }
        return true
    }

    var winnerText: String {
        switch self {
        case .playing: return ""
        case .redWins: return "红队获胜！"
        case .blueWins: return "蓝队获胜！"
        case .assassinRevealed(let team):
            return "\(team.displayName)触碰刺客，\(team.opposite.displayName)获胜！"
        }
    }
}

struct Card: Identifiable {
    let id = UUID()
    let word: String
    let color: CardColor
    var isRevealed: Bool = false
}

let codenamesWordList: [String] = [
    "苹果", "银行", "蝙蝠", "海滩", "熊",
    "床", "钟", "船", "炸弹", "书",
    "盒子", "桥", "相机", "城堡", "猫",
    "细胞", "椅子", "胸", "中国", "巧克力",
    "教堂", "电路", "时钟", "云", "大衣",
    "代码", "硬币", "冷", "领子", "颜色",
    "计算机", "烹饪", "铜", "王冠", "水晶",
    "舞蹈", "黑暗", "日期", "死亡", "沙漠",
    "钻石", "骰子", "门", "龙", "鼓",
    "地球", "埃及", "象", "能量", "引擎",
    "眼睛", "面部", "火", "鱼", "旗",
    "花", "森林", "狐狸", "青蛙", "游戏",
    "宝石", "幽灵", "玻璃", "金", "绿色",
    "锤子", "手", "帽子", "头", "心",
    "热", "冰", "图像", "日本", "钥匙",
    "国王", "刀", "灯", "叶", "生命",
    "狮子", "魔法", "地图", "月亮", "山",
    "音乐", "海洋", "橙", "书页", "纸",
    "钢笔", "手机", "飞机", "行星", "植物",
    "平台", "毒药", "力量", "女王", "兔子",
    "彩虹", "环", "岩石", "玫瑰", "学校",
    "剪刀", "种子", "船", "银", "天空",
    "烟", "雪", "音响", "蜘蛛", "明星",
    "石头", "太阳", "剑", "塔", "虎",
    "时间", "树", "水", "风", "世界",
]
