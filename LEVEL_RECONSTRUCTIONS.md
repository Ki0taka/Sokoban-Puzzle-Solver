# Figure 4 Level Reconstructions

The official figures are raster images with faint grid lines. These are the
current cell-by-cell text reconstructions used by the solver. Coordinates, when
mentioned, are zero-based `(row, column)`.

## Example 1 — 4×4 interior room

Six rows and columns: one target in the upper-left interior cell, a box in the
top row, player directly below the box, and a wall to the player's left.

```text
OOOOOO
OS B O
O OR O
O    O
O    O
OOOOOO
```

No visible object position is uncertain. The printed figure shows four interior
floor columns and four interior floor rows.

## Example 2 — central wall and narrow right passage

The player is drawn over the target, so it is encoded as `.`. The box is in the
lower-left open area. The central wall has a horizontal section and a downward
spur; a narrow passage runs down its right side.

```text
OOOOOOOOO
O       O
O       O
O  OOO  O
O    O. O
O     O O
O  B  O O
O     O O
OOOOOOOOO
```

**Uncertain cells:** the image does not make the exact length of the horizontal
wall and its one-cell spur completely clear. This version uses three cells in
the horizontal section, a one-cell spur, and puts the box at `(6, 3)`. The
player/target cell is read as `(4, 6)`.

## Example 3 — upper room with a two-target vertical arm

There are two boxes: one immediately left of the player in the upper room and
one at the entrance to the right-hand arm. The two targets are vertically
stacked in the far-right target column.

```text
OOOOOOOO
O   O  O
O  BR  O
O      O
OOOOO BO
OOOOO SO
OOOOO SO
OOOOOOOO
```

**Uncertain cells:** the source image is least precise where the upper room
narrows into the target arm. This version places the arm box at `(4, 6)`, the
targets at `(5, 6)` and `(6, 6)`, and the connecting floor at column 5.

## Example 4 — three boxes, including one already on a target

The upper box is encoded as `*`. In the row below, two boxes are separated by a
wall. The row beneath them has target, player, target in that order.

```text
OOOOOOOOO
OO  OOOOO
OO  OOOOO
OO *   OO
OOBOB  OO
O SRS  OO
O      OO
OO  OOOOO
OO  OOOOO
OOOOOOOOO
```

**Uncertain cells:** the object order and central separating wall are clear.
The precise length of the side passages below the target row is harder to count;
this reconstruction uses a two-cell lower stem.

## Example 5 — cross-shaped warehouse

The map contains three boxes and three targets. The targets are at the upper
stem, right arm, and lower stem; boxes occupy the left arm, upper-right area,
and lower stem, with the player near the center.

```text
OOOOOOOOOO
OOO S  OOO
O        O
O B R B  O
O      S O
OOO    OOO
OOOB   OOO
OOO  S OOO
OOO    OOO
OOOOOOOOOO
```

**Uncertain cells:** object locations are read from the centers of the visible
tiles. The exact one-cell wall notches where the arms meet the central/lower
corridor are ambiguous at the PDF resolution; this version models the broad
cross outline and uses the enclosed corridor shown above.

## Example 6 — Figure 7 Example 1 (two-chamber warehouse)

A 7×7 grid. The left part is 2 columns wide with 3 targets along its left wall (rows 1, 3, 5).
A one-cell doorway through the middle row joins it to the right chamber.
The right chamber is 2 columns wide with 3 boxes stacked vertically in its left column (rows 2, 3, 4)
and the player in the upper-right corner.

```text
OOOOOOO
OS O RO
O  OB O
OS  B O
O  OB O
OS O  O
OOOOOOO
```

**Uncertain cells:**
- Row 1: Player at `(1, 5)`. The player tile could potentially have been at `(1, 4)`, but the visual alignment and prompt specification explicitly place the player in the top-right corner `(1, 5)` adjacent to the outer wall.
- Row 3 Doorway: Exactly one cell wide at `(3, 3)`. The visual divider between the two rooms is solid walls except for this center corridor.

## Example 7 — Figure 7 Example 2 (stepped room with cluster)

An 8×6 grid with stepped perimeter walls. 4 targets arranged as a 3-wide horizontal row and 1 centered below.
4 boxes with one placed to the upper right of the cluster and three side-by-side in the row below.
The player begins at the bottom-right floor cell.

```text
OOOOOOOO
OSSS OOO
O S B  O
O  BBB O
OOOO  RO
OOOOOOOO
```

**Uncertain cells:**
- Row 1: Columns 5, 6, 7 are solid exterior walls (`OOO`). Column 4 is open floor (` `) allowing player traversal behind the boxes.
- Row 4: Columns 0 to 3 are solid wall (`OOOO`). Floor begins at column 4 with the player at `(4, 6)`.
- Enclosure: All playable floor tiles are fully enclosed by solid wall borders; flood fill from player `(4, 6)` stays inside the bounds.
