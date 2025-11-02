from enum import Enum
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any

# ---------------- Enums & Core Data ----------------

class PowerUpState(str, Enum):
    ROUND_START = "round_start"
    MID_ROUND = "MID_ROUND"
    ROUND_END = "round_end"
    AFTER_ROUND = "after_round"

@dataclass
class PowerUp:
    name: str
    description: str
    cooldown: int
    state: PowerUpState
    effect: Optional[Callable]


def effect_future_sight(game_data) -> None:
    player = game_data.get("player")
    if player.is_correct == True:
        player.score *= 1.5
        player.score = int(player.score)
    else:
        scores = game_data.get("scores")
        top_player = max(scores, key=scores.get)
        player.score -= top_player.score

def effect_sword_of_justice(game_data) -> None:
    player = game_data.get("player")
    scores = game_data.get("scores")
    target_player = game_data.get("target_player")
    if target_player.active_powerup == "iron_heart":
        return
    if target_player.active_powerup == "mirror_shield":
        player.score -= int(1.5 * scores[target_player])
        target_player.score -= scores[target_player]
        player.active_powerup = None
        return
    
    if player.is_correct == True:
        player.score -= scores[player]
        target_player.score -= int(1.5 * scores[player])

def effect_decay(game_data) -> None:
    player = game_data.get("player")
    scores = game_data.get("scores")
    target_player = game_data.get("target_player")
    if target_player.active_powerup == "iron_heart":
        return
    if target_player.active_powerup == "mirror_shield":
        if target_player.is_correct == True and player.is_correct == False:
            player.score -= scores[target_player]
        player.active_powerup = None
        return
    
    if player.is_correct == True and target_player.is_correct == False:
        target_player.score -= scores[player]

def effect_parasite(game_data) -> None:
    player = game_data.get("player")
    scores = game_data.get("scores")
    target_player = game_data.get("target_player")
    if target_player.active_powerup == "iron_heart":
        return
    if target_player.active_powerup == "mirror_shield":
        if player.is_correct == False:
            target_player.score -= scores[target_player]
        elif player.is_correct == True:
            target_player.score += 0.4 * scores[player]
            player.score -= 0.4 * scores[player]
        player.active_powerup = None
        return
    
    if target_player.is_correct == False:
        player.score -= scores[player]
    elif target_player.is_correct == True:
        player.score += 0.4 * scores[target_player]
        target_player.score -= 0.4 * scores[target_player]

def effect_shared_destiny(game_data) -> None:
    player = game_data.get("player")
    scores = game_data.get("scores")
    target_player = game_data.get("target_player")
    averged_score = (player.score + target_player.score)/2
    
    if averged_score > target_player.score:
        if target_player.active_powerup == "iron_heart":
            return
    
    player.score -= scores[player]
    target_player.score -= scores[target_player]
    
    player.score += averged_score
    target_player.score += averged_score

def effect_robber(game_data) -> None:
    player = game_data.get("player")
    scores = game_data.get("scores")
    target_player = game_data.get("target_player")
    if target_player.is_correct == True:
        player.score += scores[target_player]

def effect_decoy(game_data) -> None:
    pass

def effect_invisibility(game_data) -> None:
    pass

def effect_mind_reading(game_data) -> None:
    pass

def effect_sneak_peek(game_data) -> None:
    pass

def effect_confusion(game_data) -> None:
    pass

def effect_kitten_storm(game_data) -> None:
    target_player = game_data.get("target_player")
    if target_player.active_powerup == "focus_field":
        return
    if target_player.active_powerup == "mirror_shield":
        player = game_data.get("player")
        player.active_powerup = None
        player.send_data({"attack": "kitten_storm", "action": "mirror_shield"})
    target_player.send_data({"attack": "kitten_storm"})

def effect_reshuffle(game_data) -> None:
    target_player = game_data.get("target_player")
    if target_player.active_powerup == "focus_field":
        return
    if target_player.active_powerup == "mirror_shield":
        player = game_data.get("player")
        player.active_powerup = None
        player.send_data({"attack": "reshuffle", "action": "mirror_shield"})
    target_player.send_data({"attack": "reshuffle"})

def effect_reflection(game_data) -> None:
    target_player = game_data.get("target_player")
    if target_player.active_powerup == "focus_field":
        return
    if target_player.active_powerup == "mirror_shield":
        player = game_data.get("player")
        player.active_powerup = None
        player.send_data({"attack": "tornado", "action": "mirror_shield"})
    target_player.send_data({"attack": "reflection"})
    
def effect_tornado(game_data) -> None:
    target_player = game_data.get("target_player")
    if target_player.active_powerup == "focus_field":
        return
    if target_player.active_powerup == "mirror_shield":
        player = game_data.get("player")
        player.active_powerup = None
        player.send_data({"attack": "tornado", "action": "mirror_shield"})
    target_player.send_data({"attack": "tornado"})

def effect_flashbang(game_data) -> None:
    target_player = game_data.get("target_player")
    if target_player.active_powerup == "focus_field":
        return
    if target_player.active_powerup == "mirror_shield":
        player = game_data.get("player")
        player.send_data({"attack": "flashbang", "action": "mirror_shield"})
    target_player.send_data({"attack": "flashbang"})

def effect_close_enough(game_data) -> None:
    pass

def effect_teleportation(game_data) -> None:
    pass

def effect_the_great_depression(game_data) -> None:
    pass

def effect_double_trouble(game_data) -> None:
    pass

def effect_rich_get_richer(game_data) -> None:
    pass

def effect_fading_light(game_data) -> None:
    pass

def default_effect() -> None:
    pass

POWERUPS: Dict[str, PowerUp] = {
    "future_sight": PowerUp(
        name="Future Sight",
        description="In the next round, earn ×1.5 points if you answer correctly. "
                    "If you get it wrong, you lose the same amount of points the first player earned for that round. "
                    "(If nobody gets it right, you don’t lose anything.)",
        cooldown=2,
        state=PowerUpState.ROUND_END,
        effect=effect_future_sight
    ),
    "sword_of_justice": PowerUp(
        name="Sword of Justice",
        description="This round you don’t keep your points. Instead, you deal 1.5x the points you would have earned to a chosen player, subtracting them from their score.",
        cooldown=2,
        state=PowerUpState.ROUND_END,
        effect=effect_sword_of_justice
    ),
    "decay": PowerUp(
        name="Decay",
        description="Pick a player. If you get it right and they don’t, you gain your points and they lose the same amount.",
        cooldown=2,
        state=PowerUpState.ROUND_END,
        effect=effect_decay
    ),
    "parasite": PowerUp(
        name="Parasite",
        description="Choose a player. If they score this round, you gain 40% of their points. If they fail, you earn nothing.",
        cooldown=3,
        state=PowerUpState.ROUND_END,
        effect=effect_parasite
    ),
    "shared_destiny": PowerUp(
        name="Shared Destiny",
        description="Pick a player. At the end of the round, your scores are averaged and both of you receive that amount.",
        cooldown=3,
        state=PowerUpState.ROUND_END,
        effect=effect_shared_destiny
    ),
    "robber": PowerUp(
        name="Robber",
        description="Choose another player. At the end of the round, you earn points if either your answer or theirs is correct.",
        cooldown=3,
        state=PowerUpState.ROUND_END,
        effect=effect_robber
    ),

    # Trick & Deception
    "decoy": PowerUp(
        name="Decoy",
        description="In the results screen, a fake 'decoy' shows up as if you submitted the opposite answer. Other players won’t know what you actually answered.",
        cooldown=3,
        state=PowerUpState.AFTER_ROUND,
        effect=effect_decoy
    ),
    "invisibility": PowerUp(
        name="Invisibility",
        description="In the results screen, your answer and score are hidden from everyone but you.",
        cooldown=3,
        state=PowerUpState.AFTER_ROUND,
        effect=effect_invisibility
    ),
    "mind_reading": PowerUp(
        name="Mind Reading",
        description="You can see every player’s submitted answer as soon as they lock it in.",
        cooldown=4,
        state=PowerUpState.MID_ROUND,
        effect=effect_mind_reading
    ),
    "sneak_peek": PowerUp(
        name="Sneak Peek",
        description="Get to see another player's power-up build.",
        cooldown=2,
        state=PowerUpState.ROUND_START,
        effect=effect_sneak_peek
    ),
    "confusion": PowerUp(
        name="Confusion",
        description="On round start reshuffle everyone's scores (doesn’t actually change your score). Your score will return next round.",
        cooldown=3,
        state=PowerUpState.AFTER_ROUND,
        effect=effect_confusion
    ),

    # Sabotage & Chaos
    "kitten_storm": PowerUp(
        name="Kitten Storm",
        description="Cover a target player’s screen with playful kittens for a few seconds at the start of the round.",
        cooldown=2,
        state=PowerUpState.ROUND_START,
        effect=effect_kitten_storm
    ),
    "reshuffle": PowerUp(
        name="Reshuffle",
        description="Randomly reorder another player’s numpad for the whole round.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=effect_reshuffle
    ),
    "reflection": PowerUp(
        name="Reflection",
        description="Flip a player’s entire screen horizontally, forcing them to adapt.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=effect_reflection
    ),
    "tornado": PowerUp(
        name="Tornado",
        description="A targeted player’s numpad buttons drift and move around randomly while they’re trying to answer.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=effect_tornado
    ),
    "flashbang": PowerUp(
        name="Flashbang",
        description="The targeted player’s screen goes completely white for the first 2 seconds of the round.",
        cooldown=2,
        state=PowerUpState.ROUND_START,
        effect=effect_flashbang
    ),

    # Defense
    "focus_field": PowerUp(
        name="Focus Field",
        description="Block all visual effects aimed at you for the next round.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=default_effect
    ),
    "mirror_shield": PowerUp(
        name="Mirror Shield",
        description="The next attack that targets you is reflected back to the caster.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=default_effect
    ),
    "iron_heart": PowerUp(
        name="Iron Heart",
        description="Block all negative score effects aimed at you for the next round.",
        cooldown=3,
        state=PowerUpState.ROUND_END,
        effect=default_effect
    ),
    "close_enough": PowerUp(
        name="Close Enough",
        description="If your answer is within ±5 of the correct answer, you still earn half points.",
        cooldown=3,
        state=PowerUpState.ROUND_END,
        effect=effect_close_enough
    ),

    # Special / Round-Changing
    "teleportation": PowerUp(
        name="Teleportation",
        description="Swap your entire power-up build with another player for the next round. (All cooldowns stay as they were.)",
        cooldown=3,
        state=PowerUpState.AFTER_ROUND,
        effect=effect_teleportation
    ),
    "the_great_depression": PowerUp(
        name="The Great Depression",
        description="The next round’s question is much harder, but everyone earns double points if they get it right.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=effect_the_great_depression
    ),
    "double_trouble": PowerUp(
        name="Double Trouble",
        description="The next round gives two different questions at once, and you get points for both.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=effect_double_trouble
    ),
    "rich_get_richer": PowerUp(
        name="Rich Get Richer",
        description="At the end of the round 20% of each player's score gets added to a pool, and the next round's winner gets it all.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=effect_rich_get_richer
    ),
    "fading_light": PowerUp(
        name="Fading Light",
        description="After 3 seconds the question fades from the host’s screen.",
        cooldown=3,
        state=PowerUpState.ROUND_START,
        effect=effect_fading_light
    ),
}
