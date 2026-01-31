# Deliberation Guide - Phase 2

The deliberation engine is now implemented! Here's how to use it.

## Quick Start - Demo Script

The easiest way to see everything in action:

```bash
cd assemblysim/backend

# Quick demo (6 citizens, no briefing, ~5 minutes)
python demo_deliberation.py --mode quick

# Full demo (8 citizens, with Perplexity briefing, ~10 minutes)
python demo_deliberation.py --mode full

# Custom topic
python demo_deliberation.py --topic "Should cities ban single-use plastics?" --citizens 8
```

The demo will:
1. Create an assembly
2. Generate citizen personas from GSS data
3. Optionally generate a briefing book
4. Run the full deliberation (opening → rounds → voting → report)
5. Display results including vote tally, themes, and reasoning

## API Usage

### 1. Start the Server

```bash
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

### 2. Create an Assembly

```bash
curl -X POST http://localhost:8000/assemblies \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Should the United States implement a Universal Basic Income?",
    "num_citizens": 8,
    "num_rounds": 2
  }'
```

This starts background citizen generation. Response:
```json
{
  "id": 1,
  "topic": "Should the United States implement...",
  "status": "pending",
  "num_citizens": 8
}
```

### 3. Poll Status

```bash
curl http://localhost:8000/assemblies/1
```

Wait for `status` to become `"citizens_ready"` or `"ready"`.

### 4. Generate Briefing (Optional)

```bash
curl -X POST http://localhost:8000/assemblies/1/briefing \
  -H "Content-Type: application/json" \
  -d '{"depth": "standard"}'
```

Wait for status to become `"ready"`.

### 5. Start Deliberation

```bash
curl -X POST http://localhost:8000/assemblies/1/start
```

Response:
```json
{
  "message": "Deliberation started",
  "assembly_id": 1,
  "status": "deliberating",
  "citizens": 8
}
```

### 6. Watch Progress

**Option A: Poll messages endpoint**
```bash
curl http://localhost:8000/assemblies/1/messages
```

**Option B: WebSocket (real-time)**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/assemblies/1');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

### 7. Get Results

**Final report:**
```bash
curl http://localhost:8000/assemblies/1/report
```

**Individual votes:**
```bash
curl http://localhost:8000/assemblies/1/citizens
```

## Deliberation Flow

The `DeliberationEngine` orchestrates this flow:

```
1. OPENING
   - Moderator welcomes participants
   - Introduces the topic

2. DELIBERATION ROUNDS (e.g., 2-3 rounds)
   For each round:
   - Moderator opens round
   - Citizens respond in turn
   - Recorder summarizes round

3. VOTING
   - Moderator transitions to voting
   - Each citizen casts vote with reasoning
   - Recorder tallies votes

4. FINAL REPORT
   - Executive summary
   - Key themes
   - Vote tally
   - Minority report
   - Consensus & disagreements

5. COMPLETION
   - Status set to "completed"
   - All data saved to database
```

## Message Types

All deliberation messages are saved to the database with:

- **role**: `moderator`, `citizen`, `recorder`, `system`
- **phase**: `opening`, `deliberation`, `voting`, `closing`
- **round_number**: 1, 2, 3, etc. (null for non-round messages)
- **citizen_id**: ID of speaking citizen (null for moderator/recorder)
- **content**: The actual message text

## Database Schema

After deliberation, you'll have:

```
Assembly
├── status: "completed"
├── completed_at: timestamp
├── Citizens (each with final_vote and vote_reasoning)
├── Messages (full transcript)
└── Report (executive summary, themes, vote tally)
```

## WebSocket Updates

When connected via WebSocket, you'll receive real-time updates:

```javascript
{
  "type": "status_update",
  "status": "deliberating",
  "message": "Round 1 starting...",
  "assembly_id": 1
}

{
  "type": "new_message",
  "round": 1,
  "citizen": "Sarah Turing",
  "message": { ... }
}

{
  "type": "round_complete",
  "round": 1,
  "total_rounds": 3
}

{
  "type": "report_ready",
  "vote_tally": { "support": 5, "oppose": 2, "abstain": 1 }
}
```

## Performance Notes

- **6 citizens, 2 rounds**: ~5-7 minutes
- **8 citizens, 3 rounds**: ~10-15 minutes
- **40 citizens, 3 rounds**: ~45-60 minutes

Time is dominated by LLM API calls. With more citizens, deliberation becomes lengthy.

For demos and testing, use 6-8 citizens and 2 rounds.

## Next Steps

With Phase 2 complete, you can now:

1. **Test the full flow** using the demo script
2. **Build a frontend** to visualize deliberation in real-time
3. **Add LangGraph** for more complex orchestration (if needed)
4. **Implement group discussions** (currently all citizens deliberate together)
5. **Add fact-checking** integration for claims made during deliberation

## Troubleshooting

**"Assembly not ready for deliberation"**
- Ensure status is `citizens_ready` or `ready`
- Check that citizens exist: `GET /assemblies/{id}/citizens`

**Deliberation seems stuck**
- Check database: `SELECT status FROM assemblies WHERE id = 1;`
- Check logs for errors
- Citizens generation or LLM calls may have failed

**Vote tally doesn't add up**
- Some citizens may have voted "abstain"
- Check individual citizen records for vote details

**Briefing generation failed**
- Perplexity API key may be missing or invalid
- Fallback briefing will be used automatically
- Check `.env` for `PERPLEXITY_API_KEY`
