class AlphabetMatrix:
    """
    This class creates a matrix and fills it with a predefined pattern. For the given pattern
    coordiates are created.
    """
    def __init__(self, rows: int, cols: int) -> None:
        self.rows: int = rows
        self.cols: int = cols
        self.matrix: list[list[str]] = [[]]
        self.coordinates_list: list[tuple[int, int]] = []

    def print_matrix(self):
        for row in self.matrix:
            print(" ".join(row))

    def place_letter(self, letter: str, row: int = 0, col: int = 0) -> None:
        self.matrix = [[" " for _ in range(self.cols)] for _ in range(self.rows)]
        self.coordinates_list = []
        letter_function = getattr(self, f"place_{letter}", None)
        if letter_function:
            letter_function(row, col)

    def scale_matrix(self, scale) -> None:
        self.coordinates_list = []
        scaled_matrix = [
            [" " for _ in range(self.cols * scale)] for _ in range(self.rows * scale)
        ]

        for i in range(self.rows):
            for j in range(self.cols):
                elem = self.matrix[i][j]
                scaled_matrix[i * scale][j * scale] = elem
                if not elem.isspace():
                    self.coordinates_list.append((i * scale, j * scale, 0))

        self.matrix = scaled_matrix

    def _create_coordinates_list(self) -> None:
        for i in range(self.rows):
            for j in range(self.cols):
                if not self.matrix[i][j].isspace():
                    self.coordinates_list.append((i, j, 0))

    def get_coordinates_list(self, center=True) -> list[tuple[int, int]]:
        if center:
            center_points = tuple(
                sum(coord) / len(self.coordinates_list)
                for coord in zip(*self.coordinates_list)
            )

            # Move the center of the points to the origin (0, 0, 0)
            moved_points = [
                (x - center_points[0], y - center_points[1], z - center_points[2])
                for x, y, z in self.coordinates_list
            ]
            return moved_points

        return self.coordinates_list

    def place_A(self, row=0, col=0):
        self.matrix[row][col + 2] = "*"
        self.matrix[row + 1][col + 1] = "*"
        self.matrix[row + 1][col + 3] = "*"
        self.matrix[row + 2][col] = "*"
        self.matrix[row + 2][col + 4] = "*"
        self.matrix[row + 3][col + 2] = "*"
        self.matrix[row + 3][col] = "*"
        self.matrix[row + 3][col + 4] = "*"
        self.matrix[row + 4][col] = "*"
        self.matrix[row + 4][col + 4] = "*"

        self._create_coordinates_list()

    def place_B(self, row=0, col=0):
        for i in range(5):
            self.matrix[row + i][col] = "*"
            self.matrix[row + i][col + 4] = "*"
        self.matrix[row][col + 1] = "*"
        self.matrix[row + 2][col + 1] = "*"
        self.matrix[row + 4][col + 1] = "*"
        self.matrix[row + 1][col + 2] = "*"
        self.matrix[row + 3][col + 2] = "*"
        self.matrix[row + 2][col + 3] = "*"

        self._create_coordinates_list()

    def place_L(self, row=0, col=0):
        self.matrix[row][col] = "*"
        self.matrix[row + 4][col] = "*"
        self.matrix[row + 4][col + 4] = "*"

        self._create_coordinates_list()

    def place_S(self, row=0, col=0):
        self.matrix[row][col + 1] = "*"
        self.matrix[row][col + 2] = "*"
        self.matrix[row][col + 3] = "*"
        self.matrix[row + 1][col] = "*"
        self.matrix[row + 2][col] = "*"
        self.matrix[row + 2][col + 1] = "*"
        self.matrix[row + 2][col + 2] = "*"
        self.matrix[row + 3][col + 3] = "*"
        self.matrix[row + 4][col + 1] = "*"
        self.matrix[row + 4][col + 2] = "*"
        self.matrix[row + 4][col + 3] = "*"

        self._create_coordinates_list()

    def place_X(self, row=0, col=0):
        self.matrix[row][col] = "*"
        self.matrix[row][col + 4] = "*"
        self.matrix[row + 1][col + 1] = "*"
        self.matrix[row + 1][col + 3] = "*"
        self.matrix[row + 2][col + 2] = "*"
        self.matrix[row + 3][col + 1] = "*"
        self.matrix[row + 3][col + 3] = "*"
        self.matrix[row + 4][col] = "*"
        self.matrix[row + 4][col + 4] = "*"

        self._create_coordinates_list()

    def place_Z(self, row=0, col=0):
        for i in range(5):
            self.matrix[row][col + i] = "*"
            self.matrix[row + 4][col + i] = "*"
        self.matrix[row + 1][col + 3] = "*"
        self.matrix[row + 2][col + 2] = "*"
        self.matrix[row + 3][col + 1] = "*"

        self._create_coordinates_list()
