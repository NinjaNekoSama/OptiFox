from dataclasses import dataclass


@dataclass
class ModelParam:
    input_size: int
    hidden_size: int
    lstm_layers: int
    train_window_size: int
    test_window_size: int
    neurones_layer_2: int

    epochs: int
    learn_rate: int
    weight_decay: int
    batch_size: int
