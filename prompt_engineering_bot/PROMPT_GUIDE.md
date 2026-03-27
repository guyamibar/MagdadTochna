# Guide for Writing Card Game Rules for the AI

To ensure the AI game engine performs with 100% accuracy, your "Free Write Rules" should follow these strict guidelines:

### **1. Core Principles**
1. **Use Direct Commands ("You"):** Address the bot directly as if it is the player. Use "You" to define its specific actions
  and constraints.
   *    Bad Example: "A player should play a move if the rank matches the top pile card." (This is a description, not an instruction).
   *    Good Example: "You MUST move 1 card from MYCLOSED to P1 only if its Rank matches the card on P1."
2. **Define the Goal Clearly:** State exactly when a player wins.
    *   *Example: "Win condition: Have zero cards in MYCLOSED."*
2.   **Define the Valid moves and Illegal moves:** State exactly when a move is legal.
     *   *Example: "If a card in MYCLOSED has the same Rank OR Suit as the card on P1, then move exactly 1 matching card from MYCLOSED to P1"*
3.  **Use Explicit "If/Then" Logic:** Avoid vague descriptions.
    *   *Instead of: "Players can match cards."*
    *   *Use: "If card X has the same rank OR suit as the card on P1, then move card X from MYCLOSED to P1."*
4.  **Explicitly Name the Locations:** Use the system names (P1, P2, PUBLIC_DECK, etc.) exactly as listed below.
    *   *Example: "Always play cards onto P1."*
5.  **Handle the "No Move" Scenario:** Always specify what happens if a player has no legal move.
    *   *Example: "If no card can be played to P1, the player MUST draw from PUBLIC_DECK to MYCLOSED."*
6.  **Define Mandatory Actions:** Use the word **MUST** for required moves. This prevents the AI from skipping a turn.
7.  **Avoid Social Rules:** Do not include rules like "Say Uno" or "Don't look at cards." The AI cannot perform social actions.
8.  **Keep it Simple and number the lines:** This helps the model maintain logical structure and priority.

---

### **2. Standardized Naming Convention**
Use these exact names when describing locations in your rules:

| System Name | Description |
| :--- | :--- |
| **PUBLIC_DECK** | The single public deck for drawing. |
| **P1 to P6** | Public piles on the table (e.g., P1, P2). |
| **MYCLOSED** | The Bot's closed/hidden hand. |
| **MYOPEN** | The Bot's open/visible cards. |
| **MYDECK** | A private deck accessible only by the Bot. |
| **PLAYERi_OPEN** | Player i's open cards (e.g., PLAYER2_OPEN). |
| **PLAYERi_DECK** | Player i's deck (e.g., PLAYER3_DECK). |

---

### **3. Example of a Perfect Rule Set**
1. Goal: Be the first to have zero cards in MYCLOSED.
2. P1 is the main pile. If P1 is empty (NONE), any card can be played to it from MYCLOSED.
3. If P1 is not empty, you MUST play a card from MYCLOSED to P1 if it matches P1's rank or suit.
4. If you have NO matching cards, you MUST draw 1 card from PUBLIC_DECK to MYCLOSED.
5. After drawing, if the new card matches P1, you may play it. Otherwise, PASS your turn.
