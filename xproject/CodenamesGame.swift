//
//  CodenamesGame.swift
//  xproject
//

import Foundation
import Combine

class CodenamesGame: ObservableObject {
    @Published var cards: [Card] = []
    @Published var currentTeam: Team = .red
    @Published var isSpymasterMode: Bool = false
    @Published var gameState: GameState = .playing

    // Red goes first: 9 cards; Blue: 8 cards; Neutral: 7; Assassin: 1
    private let redCount = 9
    private let blueCount = 8
    private let neutralCount = 7
    private let assassinCount = 1

    var redRemaining: Int {
        cards.filter { $0.color == .red && !$0.isRevealed }.count
    }

    var blueRemaining: Int {
        cards.filter { $0.color == .blue && !$0.isRevealed }.count
    }

    init() {
        startNewGame()
    }

    func startNewGame() {
        let words = Array(codenamesWordList.shuffled().prefix(25))

        var colors: [CardColor] = []
        colors += Array(repeating: .red, count: redCount)
        colors += Array(repeating: .blue, count: blueCount)
        colors += Array(repeating: .neutral, count: neutralCount)
        colors += Array(repeating: .assassin, count: assassinCount)
        colors.shuffle()

        cards = zip(words, colors).map { Card(word: $0, color: $1) }
        currentTeam = .red
        isSpymasterMode = false
        gameState = .playing
    }

    func revealCard(_ card: Card) {
        guard !gameState.isOver,
              let index = cards.firstIndex(where: { $0.id == card.id }),
              !cards[index].isRevealed else { return }

        cards[index].isRevealed = true
        let revealed = cards[index]

        switch revealed.color {
        case .assassin:
            gameState = .assassinRevealed(by: currentTeam)

        case .red:
            if redRemaining == 0 {
                gameState = .redWins
            } else if currentTeam == .blue {
                // Revealed opponent's card — turn ends
                switchTeam()
            }

        case .blue:
            if blueRemaining == 0 {
                gameState = .blueWins
            } else if currentTeam == .red {
                switchTeam()
            }

        case .neutral:
            switchTeam()
        }
    }

    func endTurn() {
        guard !gameState.isOver else { return }
        switchTeam()
    }

    private func switchTeam() {
        currentTeam = currentTeam.opposite
    }
}
