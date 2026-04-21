//
//  CodenamesView.swift
//  xproject
//

import SwiftUI

struct CodenamesView: View {
    @StateObject private var game = CodenamesGame()

    private let columns = Array(repeating: GridItem(.flexible(), spacing: 6), count: 5)

    var body: some View {
        ZStack {
            Color(.systemGroupedBackground).ignoresSafeArea()

            VStack(spacing: 12) {
                headerView
                scoreView
                cardGrid
                controlRow
            }
            .padding()

            if game.gameState.isOver {
                gameOverOverlay
            }
        }
        .navigationTitle("行动代号")
    }

    // MARK: - Header

    private var headerView: some View {
        HStack {
            Text("行动代号")
                .font(.title2.bold())
            Spacer()
            Toggle("间谍主管", isOn: $game.isSpymasterMode)
                .toggleStyle(.button)
                .tint(.purple)
                .font(.caption)
        }
    }

    // MARK: - Score

    private var scoreView: some View {
        HStack(spacing: 0) {
            teamScoreChip(color: .red, label: "红队", remaining: game.redRemaining)
            Spacer()
            currentTeamBadge
            Spacer()
            teamScoreChip(color: .blue, label: "蓝队", remaining: game.blueRemaining)
        }
        .padding(.horizontal, 4)
    }

    private func teamScoreChip(color: Color, label: String, remaining: Int) -> some View {
        HStack(spacing: 4) {
            Circle().fill(color).frame(width: 10, height: 10)
            Text("\(label): \(remaining)")
                .font(.subheadline.bold())
                .foregroundColor(color)
        }
    }

    private var currentTeamBadge: some View {
        Text("\(game.currentTeam.displayName)行动")
            .font(.caption.bold())
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(game.currentTeam == .red ? Color.red : Color.blue)
            .foregroundColor(.white)
            .clipShape(Capsule())
    }

    // MARK: - Card Grid

    private var cardGrid: some View {
        LazyVGrid(columns: columns, spacing: 6) {
            ForEach(game.cards) { card in
                CardView(card: card, isSpymasterMode: game.isSpymasterMode)
                    .onTapGesture { game.revealCard(card) }
            }
        }
    }

    // MARK: - Controls

    private var controlRow: some View {
        HStack(spacing: 12) {
            Button(action: { game.endTurn() }) {
                Label("结束回合", systemImage: "arrow.right.circle")
                    .font(.subheadline.bold())
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(game.currentTeam == .red ? .red : .blue)
            .disabled(game.gameState.isOver)

            Button(action: { game.startNewGame() }) {
                Label("新游戏", systemImage: "arrow.clockwise")
                    .font(.subheadline.bold())
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .tint(.secondary)
        }
    }

    // MARK: - Game Over Overlay

    private var gameOverOverlay: some View {
        ZStack {
            Color.black.opacity(0.55).ignoresSafeArea()
            VStack(spacing: 20) {
                Text(game.gameState.winnerText)
                    .font(.title.bold())
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)
                    .padding()

                Button(action: { game.startNewGame() }) {
                    Label("再来一局", systemImage: "arrow.clockwise")
                        .font(.headline)
                        .padding(.horizontal, 32)
                        .padding(.vertical, 12)
                }
                .buttonStyle(.borderedProminent)
                .tint(.white)
                .foregroundColor(.black)
            }
            .padding()
        }
    }
}

// MARK: - CardView

struct CardView: View {
    let card: Card
    let isSpymasterMode: Bool

    private var backgroundColor: Color {
        if card.isRevealed {
            return revealedColor
        }
        if isSpymasterMode {
            return revealedColor.opacity(0.35)
        }
        return Color(.secondarySystemGroupedBackground)
    }

    private var revealedColor: Color {
        switch card.color {
        case .red:      return .red
        case .blue:     return .blue
        case .neutral:  return Color(.systemBrown).opacity(0.7)
        case .assassin: return .black
        }
    }

    private var textColor: Color {
        if card.isRevealed {
            return card.color == .neutral ? .white : .white
        }
        if isSpymasterMode {
            return card.color == .assassin ? .white : .primary
        }
        return .primary
    }

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 8)
                .fill(backgroundColor)
                .shadow(color: .black.opacity(0.1), radius: 2, x: 0, y: 1)

            if isSpymasterMode && !card.isRevealed && card.color == .assassin {
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(Color.red, lineWidth: 2)
            }

            Text(card.word)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(textColor)
                .multilineTextAlignment(.center)
                .minimumScaleFactor(0.6)
                .padding(4)
        }
        .aspectRatio(1.4, contentMode: .fit)
        .opacity(card.isRevealed ? 0.75 : 1.0)
    }
}

#Preview {
    NavigationStack {
        CodenamesView()
    }
}
