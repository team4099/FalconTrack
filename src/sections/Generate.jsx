import { Navbar } from '../components/Navbar.jsx'
import QRCode from "@yzfe/qrcodejs";
import { createSignal, createEffect } from "solid-js"

const Generate = () => {

    const [qrText, setQRText] = createSignal("https://team4099.com")

    createEffect(() => {
        let qrcode = new QRCode(document.getElementById("qrcode"), {
            text: qrText(),
            width: 300,
            height: 300,
        });
    });

    createEffect(() => {
        console.log(document.getElementById("text").value)
    })

    var hello = "test";

    return ( 
        <div class="w-full bg-[#0D1117]">
            <Navbar />
            <div class="w-4/5 h-screen mx-auto mt-5">
                <h1 class="text-4xl text-white font-semibold mb-20">
                    Generate
                </h1>

                <div class="mx-auto grid place-items-center w-72 h-72 bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500" style="border-radius: 2em;">
                    <div class="w-64 h-64 grid place-items-center bg-white" style="border-radius: 1.5em;">
                        <div class="max-w-68 max-h-68 mx-auto" id="qrcode" style="margin-top: 0px; width:12rem; height: 12rem;"></div>
                    </div>
                </div>

                <input id="text" type="text" value={qrText()}
                    class="text-xl text-black h-12 rounded rounded-lg border border-4 border-gray-700"
                />

            </div>
        </div>
    );
}

export { Generate };