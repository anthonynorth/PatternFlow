import tensorflow as tf
from tensorflow.keras import models
from functools import reduce
import layers


class Perceiver(models.Model):
    def __init__(
        self,
        num_blocks: int = 8,
        num_self_attends_per_block: int = 6,
        num_cross_heads: int = 1,
        num_self_attend_heads: int = 8,
        latent_dim: int = 512,
        latent_channels: int = 1024,
        num_freq_bands: int = 64,
        num_classes: int = 2,
        name: str = "perceiver",
    ):
        super().__init__(name=name)
        self.num_blocks = num_blocks

        self.latent = layers.Latent(dim=latent_dim, num_channels=latent_channels)
        self.fourier_enc = layers.FourierPositionEmbedding(num_bands=num_freq_bands)
        self.cross_attention = layers.CrossAttention(num_heads=num_cross_heads)
        self.self_attentions = [
            layers.SelfAttention(num_heads=num_self_attend_heads)
            for _ in range(num_self_attends_per_block)
        ]
        self.logits = layers.ClassificationDecoder(num_classes=num_classes)

    def call(self, inputs: tf.Tensor):
        latent_array = self.latent(inputs)
        inputs_enc = self.fourier_enc(inputs)

        def attn_block(z: tf.Tensor, *args):
            return reduce(
                lambda z, attend: attend(z),
                self.self_attentions,
                self.cross_attention(z, inputs_enc),
            )

        z = reduce(attn_block, range(self.num_blocks), latent_array)
        return self.logits(z)