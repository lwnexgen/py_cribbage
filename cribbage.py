#!/usr/bin/env python
from sources.Card import Deck, Card, Hand
from itertools import izip, groupby, combinations
from operator import itemgetter

import random, pprint, sys

pp = pprint.PrettyPrinter(indent=2)

deck = Deck()

s_Rand = random.SystemRandom()

_dealer = None

HAND="hand"
PEG="peg"
CRIB="crib"

class Player:
    def __init__(self, name):
        self.name = name
        self.score = 0
        self.hand = Hand(name)
        self.stats = {}

    def add_score(self, score, score_type=HAND):
        self.score += score        
        if score_type==PEG:
            total = self.stats.setdefault("total peg", 0.0)
            numpegs = self.stats.setdefault("number of pegs", 0.0)
            total += float(score)
            numpegs += 1.0
            self.stats['average peg'] = float(total/numpegs)
            self.stats['total peg'] = total
            self.stats['number of pegs'] = numpegs
        elif score_type==HAND:
            total = self.stats.setdefault("total hand", 0.0)
            numhands = self.stats.setdefault("number of hands", 0.0)
            total += float(score)
            numhands += 1.0
            self.stats['average hand'] = float(total/numhands)
            self.stats['total hand'] = total
            self.stats['number of hands'] = numhands
        elif score_type==CRIB:
            total = self.stats.setdefault("total crib", 0.0)
            numcribs = self.stats.setdefault("number of cribs", 0.0)
            total += float(score)
            numcribs += 1.0
            self.stats['average crib'] = float(total/numcribs)
            self.stats['total crib'] = total
            self.stats['number of cribs'] = numcribs
                                    
    def deal(self):
        deck.move_cards(hand, 6)

    def discard(self):
        discards = []
        s_Rand.shuffle(self.hand.cards)
        for i in xrange(0, 2):
            discards.append(self.hand.cards.pop())
        return discards

    def __repr__(self):
        return "%s (%s)" % (self.name, self.score)

def finished():
    for name, player in players.iteritems():
        if player.score >= 120:
            return True
    return False

def dealer():
    global _dealer

    if not _dealer:
        _dealer = players[s_Rand.choice(players.keys())]
    else:
        for name, player in players.iteritems():
            if _dealer.name != name:
                _dealer = player
                break

    print "Dealer: %s" % _dealer.name

def get_combos(cards, cut_card=None, runs=False):
    combs = []

    if cut_card:
        cards.append(cut_card)

    for i in xrange(2, len(cards)):
        combs += [
            c for c in combinations(cards, i)
        ]

    if runs:
        threes = [ sorted(c, key=lambda x: x.rank) for c in combs if len(c) >= 3 ]
        lsorted = sorted(threes, key=lambda x: len(x), reverse=True)
        return lsorted

    return combs

def get_runs(cards):
    combos = get_combos(cards, runs=True)

    runs = []
    for combo in combos:
        isrun = True
        for index, card in enumerate(combo):
            try:
                if combo[index + 1].rank != card.rank + 1:
                    isrun = False
                    break
            except:
                pass
        if isrun:
            okay = True
            for run in [ set(r) for r in runs ]:
                if set(combo).issubset(run):
                    okay = False
            if okay:
                runs.append(combo)
    return runs

def score(player, hand, cut_card, verbose):
    score = 0

    combos = get_combos(hand, cut_card)

    if verbose: print "[%s] (%s)" % (player.name, [ str(c) for c in hand ])

    # fifteens
    for combo in combos:
        tot = 0
        for card in combo:
            tot += min(10, card.rank)
        if tot == 15:
            score += 2
            if verbose: print "[%s] fifteen-%s (%s)" % (player.name, score, ", ".join([ str(c) for c in combo ]))
            
    # pairs
    pairs = []
    for combo in [ c for c in combos if len(c) == 2 ]:
        if combo[0].rank == (combo[1].rank):
            score += 2
            pairs.append(combo)
            if verbose: print "[%s] a pair for %s (%s)" % (player.name, score, ", ".join([ str(c) for c in combo ]))

    # runs
    runs = get_runs(hand + [cut_card])
    for run in runs:
        score += len(run)
        if verbose: print "[%s] a run of %s for %s (%s)" % (player.name, len(run), score, ", ".join([ str(c) for c in run ]))

    # knobs
    for card in hand:
        if card.rank == 11 and card.suit == cut_card.suit:
            score += 1
            if verbose: print "[%s] knobs for %s (%s, %s)" % (player.name, score, card, cut_card)

    # suited
    suit = hand[0].suit
    valid = True
    for card in hand:
        if card.suit != suit:
            valid = False
            break

    if valid:
        score += len(hand)
        if cut_card.suit == suit:
            score += 1
            if verbose: print "[%s] 5 %s for %s" % (player.name, suit, score)
        else:
            if verbose: print "[%s] 4 %s for %s" % (player.name, suit, score)

    return score

def score_pegging_card(card, pegging_score, previously_played):
    score = 0

    # pairs
    group = set([])
    for prev in reversed(previously_played):
        if prev.rank == card.rank:
            group.add(prev)
            group.add(card)
        else:
            break

    score += (2 * len([ c for c in combinations(group, 2) ]))

    # fifteens and thirty-one:
    if pegging_score + min(10, card.rank) == 15:
        score += 2
    elif pegging_score + min(10, card.rank) == 31:
        score += 2

    runs = get_runs(previously_played)

    if runs:
        revd = list(reversed(previously_played))
        for run in runs:
            valid = True
            sliced = revd[(-1 * len(run)):]
            for card in run:
                if card not in sliced:
                    valid = False
                    break
            if valid:
                score += len(run)

    return score

def get_pegging_card(hand, pegging_score, previously_played):
    for index, card in enumerate(hand):
        if pegging_score + min(10, card.rank) <= 31:
            return (hand.pop(index), score_pegging_card(card, pegging_score, previously_played))
    return (None, 0)

def peg(verbose=False):
    for name, player in players.iteritems():
        if name != _dealer.name:
            not_dealer = player

    cards = {
        _dealer.name: list(_dealer.hand.cards),
        not_dealer.name: list(not_dealer.hand.cards)
    }

    first = not_dealer
    pegging_count = 0
    previously_played = []
    go = False
    reset = False

    while len(cards[_dealer.name]) or len(cards[not_dealer.name]):
        played_card, played_score = get_pegging_card(cards[first.name], pegging_count, previously_played)

        if played_card:
            previously_played.append(played_card)
            pegging_count += min(10, played_card.rank)
        elif go:
            if len(cards[first.name]):
                if verbose: print "[%s] Go for me! (%s)" % (first.name, ", ".join([ str(x) for x in cards[first.name] ]))
            else:
                if verbose: print "[%s] Go for me!"
            played_score += 1
            reset = True
        else:
            if len(cards[first.name]):
                if verbose: print "[%s] Go! (%s)" % (first.name, ", ".join([ str(x) for x in cards[first.name] ]))
            else:
                if verbose: print "[%s] Go!"
            go = True

        if played_score > 1:
            if verbose: print "[%s] %s for %s (%s)" % (first.name, pegging_count, played_score, played_card)
        elif not go:
            if verbose: print "[%s] %s (%s)" % (first.name, pegging_count, played_card)

        first.add_score(played_score, score_type=PEG)

        if first.name == _dealer.name and cards[not_dealer.name]:
            first = not_dealer
        elif first.name == not_dealer.name and cards[_dealer.name]:
            first = _dealer

        if reset or pegging_count == 31:
            previously_played = []
            pegging_count = 0
            go = False
            reset = False

def play():
    for name, player in players.iteritems():
        player.score = 0

    while not finished():
        dealer()

        deck = Deck()
        deck.shuffle()

        _dealer.crib = Hand()

        # Deal and set cribs
        for name, player in players.iteritems():
            player.hand = Hand(name)
            deck.move_cards(player.hand, 6)
            _dealer.crib.cards += player.discard()
            if player.name != _dealer.name:
                try:
                    del(player.crib)
                except:
                    pass
                not_dealer = player

        # Get a cut card
        deck.shuffle()
        cut_card = deck.pop_card()
        
        # Peg
        verbose = True
        peg(verbose=verbose)
        not_dealer.add_score(score(not_dealer, not_dealer.hand.cards, cut_card, verbose=verbose))
        _dealer.add_score(score(_dealer, _dealer.hand.cards, cut_card, verbose=verbose))
        if verbose: print "[%s] and in my crib" % (_dealer.name)
        _dealer.add_score(score(_dealer, _dealer.crib.cards, cut_card, verbose=verbose), score_type=CRIB)

        for name, player in players.iteritems():
            print "%s: %s" % (player.name, player.score)

    if (players[players.keys()[0]].score) > (players[players.keys()[1]].score):
        print "%s wins!" % players[players.keys()[0]]
    else:
        print "%s wins!" % players[players.keys()[1]]

if __name__ == '__main__':
    players = {
        'Random': Player('Random'),
        'Good': Player('Good')
    }

    games = 1

    try:
        games = int(sys.argv[1])
    except Exception as exc:
        import pdb ; pdb.set_trace()
    
    for i in xrange(0, games):
        play()
    
    for key, player in players.iteritems():
        print player.name
        pp.pprint(player.stats)
