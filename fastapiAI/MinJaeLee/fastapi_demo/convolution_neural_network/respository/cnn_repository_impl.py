import io
import os

import numpy as np
from PIL import Image
from fastapi import HTTPException
from tensorflow.python.client import device_lib
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from convolution_neural_network.respository.cnn_repository import ConvolutionNeuralNetworkRepository
from tensorflow.keras import datasets, models, layers


class ConvolutionNeuralNetworkRepositoryImpl(ConvolutionNeuralNetworkRepository):
    def loadCifar10Data(self):
        print(f"repository -> loadCifar10Data()")

        return datasets.cifar10.load_data()

    def filteringClasses(self, imageList, labelList, targetClassList):
        print(f"repository -> filteringClasses()")
        filterMask = np.isin(labelList, targetClassList).flatten()
        filteredImageList = imageList[filterMask]
        filteredLabelList = labelList[filterMask]

        # print(f"filteredImageList: {filteredImageList} length: {len(filteredImageList)}")
        # print(f"filteredLabelList: {filteredLabelList} length: {len(filteredLabelList)}")

        for index, classIndex in enumerate(targetClassList):
            filteredLabelList[filteredLabelList == classIndex] = index

        # print(f"filteredLabelList: {filteredLabelList} length: {len(filteredLabelList)}")

        return filteredImageList, filteredLabelList

    def createDataGenerator(self, trainImageList, trainLabelList, testImageList, testLabelList):
        print(f"repository -> createDataGenerator()")

        # 실질적으로 픽셀은 0~ 255에 해당함
        # 그러나 그래픽 카드는 0.xxx 도 표현할 수 있음
        # 고로 256개의 픽셀만 제어하는 것이 아니라 그 사이의 소수점까지 모두 다를 수 있음
        # 계산 정밀도를 높이기 위해 소수점인 0~ 1로 변환하는 것임

        # 이미지를 랜덤하게 40도까지 회전시키면서 학습함
        # 랜덤하게 가로방향 20%이동
        # 높이에 대해서도 동일
        # 기울여서 분석 정밀도를 더 높임
        # 이미지를 랜덤하게 20%까지 확대, 축소하여 추가로 분석 정밀도를 높임
        # 또한 뒤집기까지 시전하여 더더욱 정밀도를 높임
        # 이미지 변환 이후 빈 공간이 있다면 가장 가까운 픽셀로 값을 채움(fill)
        trainDataGenerator = ImageDataGenerator(rescale=1. / 255, rotation_range=40, width_shift_range=0.2,
                                                height_shift_range=0.2, shear_range=0.2, zoom_range=0.2,
                                                horizontal_flip=True, fill_mode='nearest', )

        testDataGenerator = ImageDataGenerator(rescale=1. / 255)

        trainGenerator = trainDataGenerator.flow(trainImageList, trainLabelList, batch_size=32)
        testGenerator = testDataGenerator.flow(testImageList, testLabelList, batch_size=32)

        return trainGenerator, testGenerator

    def createModel(self, inputShape, numberOfClass):
        print(f"repository -> createModel()")

        model = models.Sequential()

        # 아래 CNN모델은 사실 그냥 어림짐작으로 맞춘 부분들입니다
        # 그냥 아마도 이럴것이다~ 하고 시작하고 보는 것이죠
        # 총 32개의 필터를 사용해서 (3, 3) 행렬로 전체 이미지를 스캔합니다
        model.add(layers.Conv2D(32, (3, 3), activation='relu', input_shape=inputShape))
        # (2, 2) 크기로 전체를 스캔하면서 이미지의 최대값을 출력합니다
        # 최대값만 뽑기 때문에 세부 사항이 묻혀서 사실상 다운 샘플링이 됩니다
        # 그리고 최대값만 뽑기 때문에 연산이나 계산 시 발생하는 비용을 최소화 할 수 있습니다
        # 결국 이를 기반으로 실질적으로 주요한 특징만 추출해 볼 수 있습니다
        model.add(layers.MaxPooling2D((2, 2)))
        # 점진적으로 필터의 숫자를 늘리면서 시도합니다
        model.add(layers.Conv2D(64, (3, 3), activation='relu'))
        model.add(layers.MaxPooling2D((2, 2)))
        model.add(layers.Conv2D(128, (3, 3), activation='relu'))
        model.add(layers.MaxPooling2D((2, 2)))
        # 쭉 진행하고 다차원 배열로 구성된 것을 1차원 배열(벡터)로 변환합니다
        # Dense 레이어에서 사용할 수 있도록 만들기 위함이라 봐도 무방
        model.add(layers.Flatten())
        # 최종적으로 위 모델을 통과한 이후 총 512개의 뉴런을 거치며 학습을 진행
        # 계산 결과가 음수값인 경우 0으로 만드는 작업 또한 relu에서 진행됨
        model.add(layers.Dense(512, activation='relu'))
        # 최종적으로 softmax를 사용해서 이것이다 저것이다로 판정을 지원
        # 이를 위해 분류하는 개수가 지정되어 있음
        model.add(layers.Dense(numberOfClass, activation='softmax'))

        # 위 구성은 고정값이 아니라 실험치나 경험적 튜닝이 될 수 있기 때문에
        # 숫자를 바꿔가며 더 좋은 구성을 찾는 [실험]이 반복 될 수 있습니다
        # 좋게 말해서 실험/ 나쁘게 말하면 노가다
        return model

    def modelCompile(self, model):
        print(f"repository -> model()")
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

        return model

    def fitModel(self, compiledModel, trainGenerator, testGenerator):
        print(f"repository -> fitModel()")
        import tensorflow as tf
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        print(device_lib.list_local_devices())
        compiledModel.fit(trainGenerator, epochs=100, validation_data=testGenerator)

        return compiledModel

    def readImageFile(self, file):
        print(f"repository -> readImageFile()")
        try:
            image = Image.open(io.BytesIO(file))
            return image
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"파일 읽는 중 문제 발생: {e}")

    def loadModel(self, savedModelPath):
        print(f"repository -> loadModel()")
        return load_model(savedModelPath)

    def predict(self, image, loadedModel):
        print(f"repository -> predict()")
        resizedImage = image.resize((32, 32))
        rgbConvertedImage = resizedImage.convert('RGB')
        arrayImage = np.array(rgbConvertedImage)
        dimExpandedArrayImage = np.expand_dims(arrayImage, axis=0)
        scaledImage = dimExpandedArrayImage / 255.0

        prediction = loadedModel.predict(scaledImage)
        return prediction
