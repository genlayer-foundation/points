# Management Commands

## update_leaderboard

Updates all frozen_global_points for contributions and recreates the leaderboard entries.

### Usage

```bash
python manage.py update_leaderboard
```

### What it does

1. Recalculates `frozen_global_points` for each contribution based on:
   - The contribution date
   - The correct multiplier that was active at that time

2. Recreates all leaderboard entries:
   - Calculates total points for each user from their contributions
   - Creates new leaderboard entries with correct point totals
   - Updates ranks for all users

This command is useful when:
- Multiplier values have been updated
- Contribution dates have been changed
- The leaderboard needs to be rebuilt from scratch
- You suspect points calculations are incorrect

## fix_invalid_multipliers

Fixes any corrupted multiplier_at_creation values in the database.

### Usage

```bash
python manage.py fix_invalid_multipliers [options]
```

### Options

- `--dry-run`: Simulate the update without making changes

### What it does

Resets all multiplier_at_creation values to 1.0 and frozen_global_points to match points. This is a quick fix for database corruption issues. After running this, you should run `update_leaderboard` to properly recalculate the points based on actual multiplier values.