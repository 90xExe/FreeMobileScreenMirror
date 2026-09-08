namespace ClearMirror.Core;

public sealed record AdbDevice(string Serial, string State, string Model, string Product)
{
    public bool IsReady => string.Equals(State, "device", StringComparison.OrdinalIgnoreCase);

    public string DisplayName
    {
        get
        {
            var model = string.IsNullOrWhiteSpace(Model) ? "Android device" : Model.Replace('_', ' ');
            var state = IsReady ? "Ready" : State;
            return $"{model}  ·  {Serial}  ·  {state}";
        }
    }
}
